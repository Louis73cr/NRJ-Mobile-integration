"""Binary sensor : seuil data 500 Go atteint (débit réduit)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import NrjLineEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NrjThresholdSensor(coordinator, msisdn)
        for msisdn in (coordinator.data or {}).get("lines", {})
    )


class NrjThresholdSensor(NrjLineEntity, BinarySensorEntity):
    """On = plafond data atteint, débit réduit (rétablissement possible)."""

    _attr_translation_key = "threshold_reached"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:speedometer-slow"

    def __init__(self, coordinator, msisdn: str) -> None:
        super().__init__(coordinator, msisdn)
        self._attr_unique_id = f"{msisdn}_threshold_reached"

    @property
    def is_on(self) -> bool:
        return bool((self.line or {}).get("threshold_reached"))
