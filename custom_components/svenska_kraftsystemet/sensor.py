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
