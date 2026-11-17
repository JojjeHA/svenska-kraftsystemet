"""UI setup for Swedish Power System."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import EntsoeClient, EntsoeAPIError
from .const import DOMAIN, CONF_API_KEY


class SwedishGridConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id("se_entsoe")
            self._abort_if_unique_id_configured()
            client = EntsoeClient(async_get_clientsession(self.hass), user_input[CONF_API_KEY])
            try:
                await client.verify_key()
            except EntsoeAPIError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Svenska kraftsystemet", data=user_input)
        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
