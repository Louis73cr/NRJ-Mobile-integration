"""Config flow UI : identifiants de l'espace client NRJ Mobile."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NrjApiError, NrjAuthError, NrjMobileClient
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str})


class NrjConfigFlow(ConfigFlow, domain=DOMAIN):
    """Flux de configuration par identifiant/mot de passe."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = NrjMobileClient(
                async_get_clientsession(self.hass),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.authenticate()
                user = await client.get_user_info()
                cid = str((user or {}).get("data", {}).get("customerId"))
            except NrjAuthError:
                errors["base"] = "invalid_auth"
            except NrjApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(cid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"NRJ Mobile {user_input[CONF_USERNAME]}", data=user_input
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
