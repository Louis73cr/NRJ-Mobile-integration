"""Base commune : une entité rattachée à un numéro (device = ligne)."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NrjCoordinator


class NrjLineEntity(CoordinatorEntity[NrjCoordinator]):
    """Entité liée à une ligne (msisdn)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NrjCoordinator, msisdn: str) -> None:
        super().__init__(coordinator)
        self._msisdn = msisdn
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, msisdn)},
            manufacturer="NRJ Mobile",
            name=f"Ligne {msisdn}",
            model=(self.line or {}).get("plan_name"),
        )

    @property
    def line(self) -> dict | None:
        return (self.coordinator.data or {}).get("lines", {}).get(self._msisdn)

    @property
    def available(self) -> bool:
        return super().available and self.line is not None
