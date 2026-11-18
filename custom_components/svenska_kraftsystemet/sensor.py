"""Sensors based on ENTSO-E reported Swedish electricity system data."""
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

# Less common categories remain in the entity registry but are disabled by
# default on new installations. Existing registry preferences are preserved.
PRODUCTION_ENABLED_BY_DEFAULT = frozenset({
    "B04",  # Naturgas
    "B12",  # Vattenkraft (magasin)
    "B14",  # Kärnkraft
    "B16",  # Solkraft
    "B19",  # Landbaserad vindkraft
    "B20",  # Övrigt
})

# Swedish display names only; the codes and unique IDs remain unchanged.
PRODUCTION_NAMES_SV = {
    "B01": "Biomassa",
    "B02": "Brunkol",
    "B03": "Kolbaserad gas",
    "B04": "Naturgas",
    "B05": "Stenkol",
    "B06": "Olja",
    "B07": "Oljeskiffer",
    "B08": "Torv",
    "B09": "Geotermisk energi",
    "B10": "Pumpkraft",
    "B11": "Vattenkraft (strömmande)",
    "B12": "Vattenkraft (magasin)",
    "B13": "Havsenergi",
    "B14": "Kärnkraft",
    "B15": "Övrig förnybar energi",
    "B16": "Solkraft",
    "B17": "Avfall",
    "B18": "Havsbaserad vindkraft",
    "B19": "Landbaserad vindkraft",
    "B20": "Övrigt",
}


def _number(value):
    return round(value, 2) if isinstance(value, (float, int)) else None


def _production(data, code):
    # This is a sum of reported generation in a category, not a verified
    # nationwide total. Missing values are not interpreted as zero.
    if any(area not in data["production"] for area in ("SE1", "SE2", "SE3", "SE4")):
        return None
    vals = [p[code] for p in data["production"].values() if code in p]
    return _number(sum(vals)) if vals and all(v is not None for v in vals) else None


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
    _attr_native_unit_of_measurement = "MW"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator, entry, key, name, getter, *, enabled_default=True):
        super().__init__(coordinator)
        self._key = key
        self._getter = getter
        self._attr_name = name
        self._attr_entity_registry_enabled_default = enabled_default
        # Keep existing unique IDs, so existing entity IDs and automations survive.
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
        return {
            "data_time_utc": moment.isoformat() if moment else None,
            "source": "ENTSO-E Transparency Platform",
            "is_live": False,
            "note": "Reported data; may be delayed or incomplete",
        }


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

    # Missing production categories are not assumed to be zero; no national
    # total-generation sensor is created at this stage.
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
