"""Sensors based on ENTSO-E reported Swedish electricity system data."""
from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import SwedishGridCoordinator
from .const import DOMAIN, BORDERS, PRODUCTION_TYPES


def _number(value):
    return round(value, 2) if isinstance(value, (float, int)) else None


def _production(data, code):
    # The category total is only reported, not a verified complete national total.
    # A category missing for an area may genuinely be absent, rather than zero.
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

    def __init__(self, coordinator, entry, key, name, getter):
        super().__init__(coordinator)
        self._key = key
        self._getter = getter
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Sveriges elsystem",
            manufacturer="ENTSO-E Transparency Platform", model="Swedish power data")

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
        return {"data_time_utc": moment.isoformat() if moment else None,
                "source": "ENTSO-E Transparency Platform", "is_live": False,
                "note": "Reported data; may be delayed or incomplete"}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    sensors = []
    for code, name in PRODUCTION_TYPES.items():
        sensors.append(SwedishGridSensor(coordinator, entry, f"production_{code}",
            f"Rapporterad produktion {name}", lambda d, code=code: _production(d, code)))
    # A missing category isn't equal to zero, and so no total-production entity is made yet.
    for area in ("SE1", "SE2", "SE3", "SE4", "SE"):
        name = "Sverige" if area == "SE" else area
        sensors.append(SwedishGridSensor(coordinator, entry, f"load_{area}",
            f"Elförbrukning {name}", lambda d, area=area: _number(d.get("load", {}).get(area))))
    for area, other in BORDERS:
        key = f"{area}_{other}"
        for direction, label in (("export", "Export"), ("import", "Import")):
            sensors.append(SwedishGridSensor(coordinator, entry, f"{direction}_{key}",
                f"{label} {area} {other}", lambda d, key=key, direction=direction: _border(d, key, direction)))
        sensors.append(SwedishGridSensor(coordinator, entry, f"net_{key}",
            f"Nettoexport {area} {other}", lambda d, key=key: _border_net(d, key)))
    for direction, label in (("export", "Export Sverige"), ("import", "Import Sverige")):
        sensors.append(SwedishGridSensor(coordinator, entry, f"total_{direction}", label,
            lambda d, direction=direction: _total_flows(d, direction)))
    sensors.append(SwedishGridSensor(coordinator, entry, "total_net", "Nettoexport Sverige", _total_net))
    async_add_entities(sensors)
