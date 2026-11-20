"""ENTSO-E data client for Svenska kraftsystemet.

Select a consistent reporting timestamp, retry transient failures, and preserve
A01/A03 time-series handling without exposing API credentials in logs.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import logging
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import API_URL, AREAS, BORDERS, PRODUCTION_TYPES

_LOGGER = logging.getLogger(__name__)
MAX_CONCURRENT_REQUESTS = 4
REQUEST_TIMEOUT_SECONDS = 20
PRODUCTION_ATTEMPTS = 3
OTHER_ATTEMPTS = 2
RETRY_BASE_DELAY_SECONDS = 2
REPORTING_STEP = timedelta(minutes=15)
INITIAL_REPORTING_DELAY = timedelta(minutes=45)
MAX_REPORTING_AGE = timedelta(hours=6)
CACHE_MAX_AGE = timedelta(minutes=60)
SWEDISH_AREAS = ("SE1", "SE2", "SE3", "SE4")
TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


class EntsoeAPIError(Exception):
    """ENTSO-E request failed; never include the API key in this message."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


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
    result = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if result <= timedelta(0):
        raise ValueError("Invalid ENTSO-E resolution")
    return result


def parse_timeseries(payload: bytes) -> list[dict]:
    """Decode XML once into valid-time ranges; do not extrapolate outside periods."""
    root = ET.fromstring(payload)
    document_type = _tag(root)
    if document_type == "Acknowledgement_MarketDocument":
        raise EntsoeAPIError("ENTSO-E returned an acknowledgement instead of data")
    if document_type not in (
        "GL_MarketDocument", "Publication_MarketDocument", "PhysicalFlow_MarketDocument",
    ):
        raise EntsoeAPIError("Unexpected ENTSO-E response type")

    readings: list[dict] = []
    for ts in root:
        if _tag(ts) != "TimeSeries":
            continue
        curve = _value(ts, "curveType")
        if curve not in ("A01", "A03"):
            _LOGGER.debug("Ignoring unsupported ENTSO-E curve type %s", curve)
            continue
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
            if end <= start:
                continue
            points: list[tuple[int, float]] = []
            for point in period:
                if _tag(point) != "Point":
                    continue
                p, q = _value(point, "position"), _value(point, "quantity")
                if p is not None and q is not None:
                    points.append((int(p), float(q)))
            points.sort()
            for idx, (position, mw) in enumerate(points):
                valid_from = start + (position - 1) * step
                if valid_from < start or valid_from >= end:
                    continue
                if curve == "A01":
                    valid_to = min(valid_from + step, end)
                else:
                    next_position = points[idx + 1][0] if idx + 1 < len(points) else None
                    valid_to = min(
                        start + (next_position - 1) * step if next_position else end,
                        end,
                    )
                if valid_to > valid_from:
                    readings.append({
                        "psr": psr, "business": business, "mw": mw,
                        "valid_from": valid_from, "valid_to": valid_to, "curve": curve,
                    })
    return readings


def readings_at(series: list[dict], moment: datetime) -> list[dict]:
    """Return only intervals actually covering this UTC time slot."""
    return [r for r in series if r["valid_from"] <= moment < r["valid_to"]]


def read_timeseries(payload: bytes, moment: datetime) -> list[dict]:
    """Compatibility helper for one reporting timestamp."""
    return readings_at(parse_timeseries(payload), moment)


def _quarter_floor(moment: datetime) -> datetime:
    return moment.replace(minute=(moment.minute // 15) * 15, second=0, microsecond=0)


def _production_values(series: list[dict]) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for reading in series:
        code = reading["psr"]
        if code not in PRODUCTION_TYPES:
            continue
        if code in values:
            values[code] = None  # Duplicate category is ambiguous, never added twice.
        else:
            values[code] = reading["mw"]
    return values


def _single_value(series: list[dict]) -> float | None:
    return series[0]["mw"] if len(series) == 1 else None


class EntsoeClient:
    def __init__(self, session: ClientSession, key: str) -> None:
        self._session = session
        self._key = key
        self._last_complete_data: dict | None = None
        self._last_complete_at: datetime | None = None

    def _use_cached_snapshot(self, now: datetime, reason: str) -> dict | None:
        """Use a consistent previous snapshot for at most 60 minutes."""
        if self._last_complete_data is None or self._last_complete_at is None:
            return None
        age = now - self._last_complete_at
        if age < timedelta(0) or age >= CACHE_MAX_AGE:
            return None
        cached = deepcopy(self._last_complete_data)
        cached["using_cached_data"] = True
        cached["cache_age_minutes"] = round(age.total_seconds() / 60, 1)
        cached["last_successful_update_utc"] = self._last_complete_at.isoformat()
        _LOGGER.warning(
            "ENTSO-E incomplete refresh (%s); retaining complete snapshot at %s UTC "
            "(cached for %.1f minutes)",
            reason, cached["moment"].isoformat(), cached["cache_age_minutes"],
        )
        return cached

    async def _request(
        self, *, document: str, period_start: datetime, period_end: datetime,
        area: str | None = None, source: str | None = None,
        dest: str | None = None,
    ) -> list[dict]:
        params = {
            "securityToken": self._key,
            "documentType": document,
            "periodStart": period_start.strftime("%Y%m%d%H%M"),
            "periodEnd": period_end.strftime("%Y%m%d%H%M"),
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
                API_URL, params=params,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            ) as response:
                if response.status != 200:
                    raise EntsoeAPIError(
                        f"ENTSO-E HTTP {response.status}",
                        retryable=response.status in TRANSIENT_HTTP_STATUSES,
                    )
                payload = await response.read()
            return parse_timeseries(payload)
        except (ClientError, asyncio.TimeoutError):
            # Never log lower-level exception messages: URLs may contain securityToken.
            raise EntsoeAPIError("ENTSO-E connection or timeout error", retryable=True) from None
        except (ET.ParseError, ValueError):
            raise EntsoeAPIError("ENTSO-E XML parsing error") from None

    async def fetch(
        self, *, document: str, moment: datetime, area: str | None = None,
        source: str | None = None, dest: str | None = None,
    ) -> list[dict]:
        """Fetch readings at one instant (used by setup key verification)."""
        start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        series = await self._request(
            document=document, period_start=start, period_end=start + timedelta(days=1),
            area=area, source=source, dest=dest,
        )
        return readings_at(series, moment)

    async def verify_key(self) -> None:
        moment = datetime.now(timezone.utc) - timedelta(days=2)
        await self.fetch(document="A65", moment=moment, area="SE3")

    async def collect(self) -> dict:
        """Collect consistent data; retry transient failures without mixing timestamps.

        Retry failed datasets selectively. A missing production zone remains absent
        if all attempts fail, so calculated national production is unavailable.
        """
        now = datetime.now(timezone.utc)
        latest = _quarter_floor(now - INITIAL_REPORTING_DELAY)
        oldest = _quarter_floor(now - MAX_REPORTING_AGE)
        candidates = []
        moment = latest
        while moment >= oldest:
            candidates.append(moment)
            moment -= REPORTING_STEP

        period_start = oldest.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = latest.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        datasets: dict[str, list[dict] | None] = {}
        request_errors: dict[str, str] = {}
        recovered: set[str] = set()

        async def load(key: str, **kwargs) -> None:
            max_attempts = PRODUCTION_ATTEMPTS if key.startswith("production_") else OTHER_ATTEMPTS
            for attempt in range(1, max_attempts + 1):
                try:
                    # Semaphore limits active HTTP calls; delays never hold a slot.
                    async with semaphore:
                        result = await self._request(
                            period_start=period_start, period_end=period_end, **kwargs
                        )
                    datasets[key] = result
                    if attempt > 1:
                        recovered.add(key)
                    request_errors.pop(key, None)
                    return
                except EntsoeAPIError as exc:
                    request_errors[key] = str(exc)
                    if not exc.retryable or attempt == max_attempts:
                        datasets[key] = None
                        return
                    await asyncio.sleep(RETRY_BASE_DELAY_SECONDS * attempt)

        # Queue generation first, then national consumption, then optional regional
        # consumption and cross-border flows. Only failed requests are retried.
        jobs = [load(f"production_{area}", document="A75", area=area)
                for area in SWEDISH_AREAS]
        jobs.append(load("load_SE", document="A65", area="SE"))
        jobs += [load(f"load_{area}", document="A65", area=area)
                 for area in SWEDISH_AREAS]
        for area, country in BORDERS:
            jobs.append(load(f"export_{area}_{country}", document="A11",
                             source=area, dest=country))
            jobs.append(load(f"import_{area}_{country}", document="A11",
                             source=country, dest=area))
        await asyncio.gather(*jobs)

        if recovered:
            _LOGGER.info(
                "ENTSO-E transient API failures recovered after retries: %s",
                ",".join(sorted(recovered)),
            )

        snapshots = []
        for candidate in candidates:
            production: dict[str, dict[str, float | None]] = {}
            consumption: dict[str, float | None] = {}
            for area in SWEDISH_AREAS:
                source = datasets.get(f"production_{area}")
                if source is not None:
                    values = _production_values(readings_at(source, candidate))
                    if values and all(v is not None for v in values.values()):
                        production[area] = values
            for area in (*SWEDISH_AREAS, "SE"):
                source = datasets.get(f"load_{area}")
                consumption[area] = (
                    _single_value(readings_at(source, candidate))
                    if source is not None else None
                )
            snapshots.append((candidate, production, consumption))

        selected = next((s for s in snapshots
                         if len(s[1]) == len(SWEDISH_AREAS)
                         and s[2]["SE"] is not None), None)
        if selected is None:
            partial = [s for s in snapshots
                       if s[2]["SE"] is not None and s[1]]
            if partial:
                selected = max(partial, key=lambda s: (len(s[1]), s[0]))
        if selected is None:
            selected = next((s for s in snapshots
                             if s[1] or any(v is not None for v in s[2].values())), None)
        if selected is None:
            if request_errors:
                _LOGGER.warning(
                    "ENTSO-E returned no usable data; failed requests: %s",
                    ", ".join(f"{key} ({reason})" for key, reason in sorted(request_errors.items())),
                )
            cached = self._use_cached_snapshot(datetime.now(timezone.utc), "no usable datasets")
            if cached is not None:
                return cached
            raise EntsoeAPIError("No production or consumption data available within six hours")

        chosen, production, consumption = selected
        errors = list(request_errors)
        for area in SWEDISH_AREAS:
            if area not in production and f"production_{area}" not in errors:
                errors.append(f"production_{area}_missing_at_timestamp")
        for area, value in consumption.items():
            if value is None and f"load_{area}" not in errors:
                errors.append(f"load_{area}_missing_at_timestamp")

        data = {
            "moment": chosen,
            "production": production,
            "load": consumption,
            "flows": {},
            "errors": errors,
        }
        for area, country in BORDERS:
            key = f"{area}_{country}"
            pair: dict[str, float | None] = {}
            for direction in ("export", "import"):
                request_key = f"{direction}_{key}"
                series = datasets.get(request_key)
                value = _single_value(readings_at(series, chosen)) if series is not None else None
                pair[direction] = value
                if value is None and request_key not in errors:
                    errors.append(f"{request_key}_missing_at_timestamp")
            data["flows"][key] = pair

        if len(production) < len(SWEDISH_AREAS):
            _LOGGER.warning(
                "ENTSO-E partial generation snapshot at %s UTC: available zones %s; "
                "missing zones %s; national load available=%s; failed API requests=%s",
                chosen.isoformat(),
                ",".join(sorted(production)) or "none",
                ",".join(area for area in SWEDISH_AREAS if area not in production),
                consumption["SE"] is not None,
                ",".join(
                    f"{key} ({reason})"
                    for key, reason in sorted(request_errors.items())
                ) or "none",
            )
        elif request_errors:
            _LOGGER.debug(
                "ENTSO-E data loaded at %s UTC; failed optional requests: %s",
                chosen.isoformat(), ",".join(sorted(request_errors)),
            )
        complete = (len(production) == len(SWEDISH_AREAS)
                    and consumption["SE"] is not None)
        if complete:
            checked_at = datetime.now(timezone.utc)
            # A complete reporting timestamp counts as new only when it is
            # strictly newer than the last accepted timestamp. Re-reading the
            # same or an older timestamp must NEVER extend the cache lifetime.
            if (self._last_complete_data is None
                    or chosen > self._last_complete_data["moment"]):
                self._last_complete_data = deepcopy(data)
                self._last_complete_at = checked_at
                data["using_cached_data"] = False
                data["cache_age_minutes"] = 0
                data["last_successful_update_utc"] = checked_at.isoformat()
                return data

            cached = self._use_cached_snapshot(
                checked_at, "no newer complete reporting timestamp"
            )
            if cached is not None:
                return cached

            # This is a valid historical snapshot, but it has not advanced
            # for at least 60 minutes. Do not publish it as fresh live data.
            # Invalidate every value together to avoid mixing timestamps.
            age = checked_at - self._last_complete_at
            _LOGGER.warning(
                "ENTSO-E complete reporting timestamp has not advanced for %.1f "
                "minutes; expired snapshot at %s UTC will not be reused",
                age.total_seconds() / 60,
                self._last_complete_data["moment"].isoformat(),
            )
            data["production"] = {}
            data["load"] = {}
            data["flows"] = {}
            data["using_cached_data"] = False
            data["cache_age_minutes"] = round(age.total_seconds() / 60, 1)
            data["cache_expired"] = True
            data["last_successful_update_utc"] = self._last_complete_at.isoformat()
            return data

        # Keep the last complete snapshot even if ENTSO-E returned a partial
        # successful response; never merge it with newer incomplete readings.
        cached = self._use_cached_snapshot(datetime.now(timezone.utc), "incomplete generation or national load")
        if cached is not None:
            return cached

        data["using_cached_data"] = False
        data["cache_age_minutes"] = 0
        data["last_successful_update_utc"] = (
            self._last_complete_at.isoformat() if self._last_complete_at else None
        )
        return data
