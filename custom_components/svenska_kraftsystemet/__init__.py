"""Svenska kraftsystemet custom integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import EntsoeClient, EntsoeAPIError
from .const import DOMAIN, CONF_API_KEY, SCAN_INTERVAL

PLATFORMS = ["sensor"]


class SwedishGridCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, client: EntsoeClient) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__),
                         name="Svenska kraftsystemet", update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.collect()
        except EntsoeAPIError as exc:
            raise UpdateFailed(str(exc)) from exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = EntsoeClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    coordinator = SwedishGridCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
