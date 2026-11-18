"""ENTSO-E data client for Svenska kraftsystemet.

Bounded parallel requests and safe A01/A03 period decoding.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import API_URL, AREAS, BORDERS, PRODUCTION_TYPES

_LOGGER = logging.getLogger(__name__)
MAX_CONCURRENT_REQUESTS = 4
REQUEST_TIMEOUT_SECONDS = 20


class EntsoeAPIError(Exception):
    """ENTSO-E request failed; messages must never contain the API key."""


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if _tag(item) == name), None)


def _value(element: ET.Element, *path: str) -> str | None:
    for name in path:
        element = _child(element, name)
        if element is None:
            return None
    return element.text.strip() if element.text else None


def _duration(value: str) -> timedelta:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match or not any(part is not None for part in match.groups()):
        raise ValueError("Unsupported ENTSO-E resolution")
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def read_timeseries(payload: bytes, moment: datetime) -> list[dict]:
    """Decode ENTSO-E time series at one UTC instant, including A03 blocks."""
    root = ET.fromstring(payload)
    root_name = _tag(root)
    if root_name == "Acknowledgement_MarketDocument":
        # Do not display server message or URL in logs, in case it echoes input.
        raise EntsoeAPIError("ENTSO-E returned an acknowledgement instead of data")
    if root_name not in (
        "GL_MarketDocument", "Publication_MarketDocument",
        "PhysicalFlow_MarketDocument",
    ):
        raise EntsoeAPIError("Unexpected ENTSO-E response type")

    readings: list[dict] = []
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
            resolution = _value(period, "resolution")
            if not start_s or not end_s or not resolution:
                continue
            start = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
            step = _duration(resolution)
            if not start <= moment < end or step.total_seconds() <= 0:
                continue
            position = int((moment - start) // step) + 1
            points: list[tuple[int, float]] = []
            for point in period:
                if _tag(point) != "Point":
                    continue
                p = _value(point, "position")
                q = _value(point, "quantity")
                if p is not None and q is not None:
                    points.append((int(p), float(q)))
            points.sort()
            chosen = None
            if curve == "A03":
                chosen = next((item for item in reversed(points) if item[0] <= position), None)
                if chosen is not None:
                    following = next((p for p, _ in points if p > chosen[0]), None)
                    effective_start = start + (chosen[0] - 1) * step
                    effective_end = start + (following - 1) * step if following else end
            elif curve == "A01":
                chosen = next((item for item in points if item[0] == position), None)
                if chosen is not None:
                    effective_start = start + (position - 1) * step
                    effective_end = effective_start + step
            else:
                _LOGGER.debug("Ignoring unsupported ENTSO-E curve type %s", curve)
            if chosen is not None:
                readings.append({
                    "psr": psr, "business": business, "mw": chosen[1],
                    "valid_from": effective_start, "valid_to": effective_end,
                    "curve": curve,
                })
    return readings


class EntsoeClient:
    def __init__(self, session: ClientSession, key: str) -> None:
        self._session = session
        self._key = key

    async def fetch(self, *, document: str, moment: datetime,
                    area: str | None = None, source: str | None = None,
                    dest: str | None = None) -> list[dict]:
        day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        params = {
            "securityToken": self._key,
            "documentType": document,
            "periodStart": day_start.strftime("%Y%m%d%H%M"),
            "periodEnd": day_end.strftime("%Y%m%d%H%M"),
        }
        if document == "A75":
            params.update({"processType": "A16", "in_Domain": AREAS[area]})
        elif document == "A65":
            params.update({"processType": "A16", "outBiddingZone_Domain": AREAS[area]})
        elif document == "A11":
            params.update({"out_Domain": AREAS[source], "in_Domain": AREAS[dest]})
        else:
            raise ValueError("Unsupported document type")
        try:
            async with self._session.get(
                API_URL, params=params, timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            ) as response:
                if response.status != 200:
                    raise EntsoeAPIError(f"ENTSO-E HTTP {response.status}")
                payload = await response.read()
            return read_timeseries(payload, moment)
        except (ClientError, asyncio.TimeoutError, ET.ParseError, ValueError):
            # Never log exceptions containing request URLs (which include securityToken).
            raise EntsoeAPIError("ENTSO-E request or XML parsing failed") from None

    async def verify_key(self) -> None:
        moment = datetime.now(timezone.utc) - timedelta(days=2)
        await self.fetch(document="A65", moment=moment, area="SE3")

    async def collect(self) -> dict:
        """Fetch all Swedish readings with at most four concurrent requests."""
        now = datetime.now(timezone.utc)
        moment = (now - timedelta(hours=3)).replace(
            minute=0, second=0, microsecond=0
        )
        data = {"moment": moment, "production": {}, "load": {}, "flows": {}, "errors": []}
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def limited_fetch(**kwargs):
            async with semaphore:
                return await self.fetch(moment=moment, **kwargs)

        async def production(area: str):
            try:
                series = await limited_fetch(document="A75", area=area)
                values: dict[str, float | None] = {}
                for reading in series:
                    code = reading["psr"]
                    if code not in PRODUCTION_TYPES:
                        continue
                    if code in values:
                        values[code] = None  # Ambiguous duplicate, not zero.
                    else:
                        values[code] = reading["mw"]
                data["production"][area] = values
            except EntsoeAPIError:
                data["errors"].append("production_" + area)

        async def consumption(area: str):
            try:
                series = await limited_fetch(document="A65", area=area)
                data["load"][area] = series[0]["mw"] if len(series) == 1 else None
            except EntsoeAPIError:
                data["load"][area] = None
                data["errors"].append("load_" + area)

        async def flow(area: str, country: str, direction: str):
            key = f"{area}_{country}"
            source, dest = (area, country) if direction == "export" else (country, area)
            try:
                series = await limited_fetch(
                    document="A11", source=source, dest=dest
                )
                value = series[0]["mw"] if len(series) == 1 else None
            except EntsoeAPIError:
                value = None
                data["errors"].append(f"{direction}_{area}_{country}")
            data["flows"].setdefault(key, {})[direction] = value

        jobs = [production(area) for area in ("SE1", "SE2", "SE3", "SE4")]
        jobs += [consumption(area) for area in ("SE1", "SE2", "SE3", "SE4", "SE")]
        for area, country in BORDERS:
            jobs.append(flow(area, country, "export"))
            jobs.append(flow(area, country, "import"))
        await asyncio.gather(*jobs)
        return data
