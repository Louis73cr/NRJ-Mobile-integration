"""Config flow UI : identifiants de l'espace client NRJ Mobile."""
from __future__ import annotations

from collections.abc import Mapping
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

    async def _validate(self, user_input: dict[str, Any], errors: dict[str, str]) -> str | None:
        """Renvoie le customerId, ou None en remplissant errors."""
        client = NrjMobileClient(
            async_get_clientsession(self.hass),
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
        )
        try:
            await client.authenticate()
            user = await client.get_user_info()
        except NrjAuthError:
            errors["base"] = "invalid_auth"
            return None
        except NrjApiError:
            errors["base"] = "cannot_connect"
            return None
        cid = ((user or {}).get("data") or {}).get("customerId")
        if cid is None:
            errors["base"] = "cannot_connect"
            return None
        return str(cid)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            cid = await self._validate(user_input, errors)
            if cid is not None:
                await self.async_set_unique_id(cid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"NRJ Mobile {user_input[CONF_USERNAME]}", data=user_input
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            cid = await self._validate(data, errors)
            if cid is not None:
                await self.async_set_unique_id(cid)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
