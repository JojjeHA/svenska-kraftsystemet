"""Read ENTSO-E Transparency Platform production, load and border flow data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientSession

from .const import API_URL, AREAS, BORDERS, PRODUCTION_TYPES

_LOGGER = logging.getLogger(__name__)


class EntsoeAPIError(Exception):
    """Remote request or response failure (never includes the API token)."""


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((x for x in element if _tag(x) == name), None)


def _path(element: ET.Element, *names: str) -> ET.Element | None:
    for name in names:
        element = _child(element, name)
        if element is None:
            return None
    return element


def _value(element: ET.Element, *names: str) -> str | None:
    node = _path(element, *names)
    return node.text.strip() if node is not None and node.text else None


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _duration(value: str) -> timedelta:
    """Support 15/30/60-minute and other integer-minute ISO 8601 resolutions."""
    import re
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match or not any(x is not None for x in match.groups()):
        raise ValueError("Unsupported resolution")
    hours, minutes, seconds = (int(x or 0) for x in match.groups())
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def read_timeseries(xml_bytes: bytes, moment: datetime) -> list[dict]:
    """Get readings valid at one UTC instant, respecting A03 variable blocks.

    Missing points aren't interpreted as zero. Distinct series are returned separately
    so a document with multiple time series can be detected instead of double counted.
    """
    root = ET.fromstring(xml_bytes)
    if _tag(root) == "Acknowledgement_MarketDocument":
        reasons = [x.text or "" for x in root.iter() if _tag(x) == "text"]
        raise EntsoeAPIError("ENTSO-E: " + "; ".join(reasons)[:250])
    if _tag(root) not in ("GL_MarketDocument", "Publication_MarketDocument", "PhysicalFlow_MarketDocument"):
        raise EntsoeAPIError("Unexpected ENTSO-E response type")
    out = []
    for ts in root:
        if _tag(ts) != "TimeSeries":
            continue
        curve = _value(ts, "curveType")
        psr = _value(ts, "MktPSRType", "psrType")
        business = _value(ts, "businessType")
        for period in ts:
            if _tag(period) != "Period":
                continue
            start_s = _value(period, "timeInterval", "start")
            end_s = _value(period, "timeInterval", "end")
            res_s = _value(period, "resolution")
            if not start_s or not end_s or not res_s:
                continue
            start, end, step = _dt(start_s), _dt(end_s), _duration(res_s)
            if not start <= moment < end or step.total_seconds() <= 0:
                continue
            position = int((moment - start) // step) + 1
            points = []
            for p in period:
                if _tag(p) != "Point":
                    continue
                idx, qty = _value(p, "position"), _value(p, "quantity")
                if idx is not None and qty is not None:
                    points.append((int(idx), float(qty)))
            points.sort()
            if curve == "A03":
                eligible = [(idx, qty) for idx, qty in points if idx <= position]
                chosen = eligible[-1] if eligible else None
                if chosen:
                    following = next((idx for idx, _ in points if idx > chosen[0]), None)
                    effective_start = start + (chosen[0] - 1) * step
                    effective_end = start + (following - 1) * step if following else end
            elif curve == "A01":
                chosen = next(((idx, qty) for idx, qty in points if idx == position), None)
                if chosen:
                    effective_start = start + (position - 1) * step
                    effective_end = effective_start + step
            else:
                _LOGGER.debug("Ignoring unsupported ENTSO-E curve type %s", curve)
                continue
            if chosen:
                out.append({"psr": psr, "business": business, "mw": chosen[1],
                            "valid_from": effective_start, "valid_to": effective_end,
                            "curve": curve})
    return out


class EntsoeClient:
    def __init__(self, session: ClientSession, key: str) -> None:
        self._session = session
        self._key = key

    async def fetch(self, *, document: str, moment: datetime, area: str | None = None,
                    source: str | None = None, dest: str | None = None) -> list[dict]:
        """Query one UTC calendar day; avoid leaking securityToken in logs/errors."""
        day = moment.strftime("%Y%m%d0000")
        next_day = (moment + timedelta(days=1)).strftime("%Y%m%d0000")
        params = {"securityToken": self._key, "documentType": document,
                  "periodStart": day, "periodEnd": next_day}
        if document == "A75":
            params.update({"processType": "A16", "in_Domain": AREAS[area]})
        elif document == "A65":
            params.update({"processType": "A16", "outBiddingZone_Domain": AREAS[area]})
        elif document == "A11":
            params.update({"out_Domain": AREAS[source], "in_Domain": AREAS[dest]})
        else:
            raise ValueError("Unsupported document")
        try:
            async with self._session.get(API_URL, params=params, timeout=40) as response:
                if response.status != 200:
                    raise EntsoeAPIError(f"ENTSO-E HTTP {response.status}")
                payload = await response.read()
            return read_timeseries(payload, moment)
        except (ClientError, asyncio.TimeoutError, ET.ParseError, ValueError) as exc:
            # Never concatenate URL or exception repr: aiohttp errors may contain the token.
            _LOGGER.debug("ENTSO-E request failed for document %s", document)
            raise EntsoeAPIError("ENTSO-E request or XML parsing failed") from None

    async def verify_key(self) -> None:
        # A query for a recent full historical day, not a future or partial interval.
        moment = datetime.now(timezone.utc) - timedelta(days=2)
        await self.fetch(document="A65", moment=moment, area="SE3")

    async def collect(self) -> dict:
        # ENTSO-E publication latency varies. Don't present very recent data as live.
        now = datetime.now(timezone.utc)
        moment = (now - timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
        data = {"moment": moment, "production": {}, "load": {}, "flows": {}, "errors": []}
        # Sequential calls (27 requests), polite to a rate-limited public API.
        for area in ("SE1", "SE2", "SE3", "SE4"):
            try:
                series = await self.fetch(document="A75", moment=moment, area=area)
                types: dict[str, float] = {}
                for reading in series:
                    code = reading["psr"]
                    if not code or code not in PRODUCTION_TYPES:
                        continue
                    # A75 can contain generation and consumption series for pumped storage.
                    # Fail closed on duplicates/unknown business semantics.
                    if code in types:
                        types[code] = None
                    else:
                        types[code] = reading["mw"]
                data["production"][area] = types
            except EntsoeAPIError:
                data["errors"].append("production_" + area)
        for area in ("SE1", "SE2", "SE3", "SE4", "SE"):
            try:
                series = await self.fetch(document="A65", moment=moment, area=area)
                data["load"][area] = series[0]["mw"] if len(series) == 1 else None
            except EntsoeAPIError:
                data["load"][area] = None
                data["errors"].append("load_" + area)
        for area, country in BORDERS:
            readings = {}
            for direction, source, dest in (("export", area, country), ("import", country, area)):
                try:
                    series = await self.fetch(document="A11", moment=moment, source=source, dest=dest)
                    readings[direction] = series[0]["mw"] if len(series) == 1 else None
                except EntsoeAPIError:
                    readings[direction] = None
                    data["errors"].append(f"{direction}_{area}_{country}")
            data["flows"][f"{area}_{country}"] = readings
        return data
