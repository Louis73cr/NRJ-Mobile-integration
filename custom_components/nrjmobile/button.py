"""Bouton : rétablir le débit web (FUP_RESET), strict gratuit."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NrjApiError
from .const import DOMAIN
from .entity import NrjLineEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NrjResetButton(coordinator, msisdn)
        for msisdn in (coordinator.data or {}).get("lines", {})
    )


class NrjResetButton(NrjLineEntity, ButtonEntity):
    """Déclenche le rétablissement du débit UNIQUEMENT si net = 0 €."""

    _attr_translation_key = "reset_debit"
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator, msisdn: str) -> None:
        super().__init__(coordinator, msisdn)
        self._attr_unique_id = f"{msisdn}_reset_debit"

    async def async_press(self) -> None:
        line = self.line or {}
        bid = line.get("billing_account_id")
        cid = self.coordinator.customer_id
        if not bid or not cid:
            raise HomeAssistantError("Ligne ou compte introuvable.")
        try:
            # allow_paid=False : refuse de soumettre si le devis n'est pas à 0 €.
            res = await self.coordinator.client.fup_reset(
                cid, bid, confirm=True, allow_paid=False
            )
        except NrjApiError as err:
            raise HomeAssistantError(f"Rétablissement refusé : {err}") from err
        if not res.get("submitted"):
            raise HomeAssistantError("Rétablissement non soumis (voir logs).")
        _LOGGER.info("Débit rétabli pour %s (net %s €)", self._msisdn, res.get("net"))
        await self.coordinator.async_request_refresh()
