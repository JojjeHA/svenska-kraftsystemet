"""Sensors for ENTSO-E reported Swedish electricity system data."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SwedishGridCoordinator
from .const import DOMAIN, BORDERS, PRODUCTION_TYPES

PRODUCTION_ENABLED_BY_DEFAULT = frozenset({
    "B04",  # Natural gas
    "B12",  # Reservoir hydro
    "B14",  # Nuclear
    "B16",  # Solar
    "B19",  # Onshore wind
    "B20",  # Other
})

PRODUCTION_NAMES_SV = {
    "B01": "Biomassa", "B02": "Brunkol", "B03": "Kolbaserad gas",
    "B04": "Naturgas", "B05": "Stenkol", "B06": "Olja",
    "B07": "Oljeskiffer", "B08": "Torv", "B09": "Geotermisk energi",
    "B10": "Pumpkraft", "B11": "Vattenkraft (strömmande)",
    "B12": "Vattenkraft (magasin)", "B13": "Havsenergi",
    "B14": "Kärnkraft", "B15": "Övrig förnybar energi",
    "B16": "Solkraft", "B17": "Avfall", "B18": "Havsbaserad vindkraft",
    "B19": "Landbaserad vindkraft", "B20": "Övrigt",
}

# These sets are mutually exclusive; together they cover every known PSR type.
GENERATION_GROUPS = {
    "nuclear": frozenset({"B14"}),
    "hydro": frozenset({"B11", "B12"}),
    "wind": frozenset({"B18", "B19"}),
}
GENERATION_GROUPS["other"] = frozenset(PRODUCTION_TYPES).difference(
    *(GENERATION_GROUPS.values())
)

SWEDISH_AREAS = ("SE1", "SE2", "SE3", "SE4")


def _number(value):
    return round(value, 2) if isinstance(value, (float, int)) else None


def _readings(data):
    """Flatten Swedish bidding-zone PSR readings from the same coordinator snapshot.

    An absent PSR is unknown, *not* an observed zero. A missing zone or an
    explicitly ambiguous value makes derived totals unavailable.
    """
    production = data.get("production", {})
    if any(area not in production for area in SWEDISH_AREAS):
        return None
    readings = []
    for area in SWEDISH_AREAS:
        for code, value in production[area].items():
            if code in PRODUCTION_TYPES:
                if value is None:
                    return None
                readings.append((code, value))
    return readings


def _production(data, code):
    # Preserve the existing per-category behavior and entity IDs.
    production = data.get("production", {})
    if any(area not in production for area in SWEDISH_AREAS):
        return None
    vals = [p[code] for p in production.values() if code in p]
    return _number(sum(vals)) if vals and all(v is not None for v in vals) else None


def _group_production(data, name):
    readings = _readings(data)
    if readings is None:
        return None
    values = [mw for code, mw in readings if code in GENERATION_GROUPS[name]]
    return _number(sum(values)) if values else None


def _total_production(data):
    readings = _readings(data)
    return _number(sum(mw for _, mw in readings)) if readings else None


def _generation_share(data, name):
    group = _group_production(data, name)
    total = _total_production(data)
    if group is None or total is None or total <= 0:
        return None
    return _number(100 * group / total)


def _production_minus_consumption(data):
    production = _total_production(data)
    consumption = _number(data.get("load", {}).get("SE"))
    return _number(production - consumption) if production is not None and consumption is not None else None


def _border(data, key, direction):
    return _number(data["flows"].get(key, {}).get(direction))


def _border_net(data, key):
    pair = data["flows"].get(key, {})
    if pair.get("export") is None or pair.get("import") is None:
        return None
    return _number(pair["export"] - pair["import"])


def _total_flows(data, direction):
    if len(data["flows"]) != len(BORDERS):
        return None
    values = [v.get(direction) for v in data["flows"].values()]
    return _number(sum(values)) if all(x is not None for x in values) else None


def _total_net(data):
    exp, imp = _total_flows(data, "export"), _total_flows(data, "import")
    return _number(exp - imp) if exp is not None and imp is not None else None


class SwedishGridSensor(CoordinatorEntity[SwedishGridCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator, entry, key, name, getter, *,
        enabled_default=True, unit="MW", device_class=SensorDeviceClass.POWER,
        calculated=False,
    ):
        super().__init__(coordinator)
        self._key = key
        self._getter = getter
        self._calculated = calculated
        self._attr_name = name
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        # Existing unique IDs are preserved across updates.
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sveriges elsystem",
            manufacturer="ENTSO-E Transparency Platform",
            model="Swedish power data",
        )

    @property
    def native_value(self):
        return self._getter(self.coordinator.data or {})

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        moment = data.get("moment")
        attrs = {
            "data_time_utc": moment.isoformat() if moment else None,
            "source": "ENTSO-E Transparency Platform",
            "is_live": False,
            "using_cached_data": data.get("using_cached_data", False),
            "cache_age_minutes": data.get("cache_age_minutes", 0),
            "last_successful_update_utc": data.get("last_successful_update_utc"),
            "note": (
                "Cached complete snapshot: values may be stale"
                if data.get("using_cached_data")
                else "Reported data; may be delayed or incomplete"
            ),
        }
        if self._calculated:
            readings = _readings(data)
            attrs["reported_psr_types"] = (
                sorted({code for code, _ in readings}) if readings is not None else []
            )
            attrs["calculation_basis"] = (
                "Reported production in SE1-SE4; unreported categories are not assumed zero"
            )
        return attrs


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    sensors = []

    for code in PRODUCTION_TYPES:
        name = PRODUCTION_NAMES_SV.get(code, PRODUCTION_TYPES[code])
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"production_{code}",
            f"Rapporterad produktion {name}",
            lambda d, code=code: _production(d, code),
            enabled_default=(code in PRODUCTION_ENABLED_BY_DEFAULT),
        ))

    # Derived readings: no helpers, extra API calls or YAML templates required.
    # Labels intentionally say "reported" because ENTSO-E may omit categories.
    for group, label in (
        ("nuclear", "Kärnkraft"),
        ("hydro", "Vattenkraft"),
        ("wind", "Vindkraft"),
        ("other", "Övrig"),
    ):
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"group_{group}",
            f"Rapporterad produktion {label} totalt",
            lambda d, group=group: _group_production(d, group),
            calculated=True,
        ))
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"share_{group}",
            f"Andel rapporterad produktion {label}",
            lambda d, group=group: _generation_share(d, group),
            unit="%", device_class=None, calculated=True,
        ))

    sensors.append(SwedishGridSensor(
        coordinator, entry, "reported_production_total",
        "Summa rapporterad produktion", _total_production,
        calculated=True,
    ))
    sensors.append(SwedishGridSensor(
        coordinator, entry, "production_minus_consumption",
        "Rapporterad produktion minus förbrukning",
        _production_minus_consumption, calculated=True,
    ))

    for area in ("SE1", "SE2", "SE3", "SE4", "SE"):
        name = "Sverige" if area == "SE" else area
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"load_{area}",
            f"Elförbrukning {name}",
            lambda d, area=area: _number(d.get("load", {}).get(area)),
        ))

    for area, other in BORDERS:
        key = f"{area}_{other}"
        for direction, label in (("export", "Export"), ("import", "Import")):
            sensors.append(SwedishGridSensor(
                coordinator, entry, f"{direction}_{key}",
                f"{label} {area} {other}",
                lambda d, key=key, direction=direction: _border(d, key, direction),
                enabled_default=False,
            ))
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"net_{key}",
            f"Nettoexport {area} {other}",
            lambda d, key=key: _border_net(d, key),
            enabled_default=False,
        ))

    for direction, label in (("export", "Export Sverige"), ("import", "Import Sverige")):
        sensors.append(SwedishGridSensor(
            coordinator, entry, f"total_{direction}", label,
            lambda d, direction=direction: _total_flows(d, direction),
        ))
    sensors.append(SwedishGridSensor(
        coordinator, entry, "total_net", "Nettoexport Sverige", _total_net,
    ))
    async_add_entities(sensors)
