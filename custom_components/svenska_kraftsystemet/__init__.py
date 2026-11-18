"""Svenska kraftsystemet custom integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EntsoeClient, EntsoeAPIError
from .const import CONF_API_KEY, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class SwedishGridCoordinator(DataUpdateCoordinator[dict]):
    """Coordinate updates without blocking the Home Assistant bootstrap."""

    def __init__(self, hass: HomeAssistant, client: EntsoeClient) -> None:
        super().__init__(hass, logger=_LOGGER, name="Svenska kraftsystemet",
                         update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.collect()
        except EntsoeAPIError as exc:
            raise UpdateFailed(str(exc)) from exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up entities first, collect the initial dataset in the background."""
    client = EntsoeClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    coordinator = SwedishGridCoordinator(hass, client)

    # Gives sensor getters a safe data structure until the first fetch finishes.
    coordinator.async_set_updated_data({
        "moment": None, "production": {}, "load": {}, "flows": {}, "errors": []
    })
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # HA background tasks do not hold up bootstrap completion.
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), "Svenska kraftsystemet initial refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
