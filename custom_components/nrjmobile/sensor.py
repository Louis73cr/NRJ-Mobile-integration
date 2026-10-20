"""Capteurs de consommation par ligne."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import NrjLineEntity


@dataclass(frozen=True, kw_only=True)
class NrjSensor(SensorEntityDescription):
    value: Callable[[dict], float | str | None]


SENSORS: tuple[NrjSensor, ...] = (
    NrjSensor(
        key="data_used",
        translation_key="data_used",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:download-network",
        value=lambda l: l.get("data_used"),
    ),
    NrjSensor(
        key="data_limit",
        translation_key="data_limit",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=0,
        icon="mdi:gauge",
        value=lambda l: l.get("data_limit"),
    ),
    NrjSensor(
        key="data_remaining",
        translation_key="data_remaining",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        icon="mdi:gauge-low",
        value=lambda l: l.get("data_remaining"),
    ),
    NrjSensor(
        key="out_of_plan_euro",
        translation_key="out_of_plan_euro",
        native_unit_of_measurement="€",
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        icon="mdi:cash-alert",
        value=lambda l: l.get("out_of_plan_euro"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NrjSensorEntity(coordinator, msisdn, desc)
        for msisdn in (coordinator.data or {}).get("lines", {})
        for desc in SENSORS
    )


class NrjSensorEntity(NrjLineEntity, SensorEntity):
    entity_description: NrjSensor

    def __init__(self, coordinator, msisdn: str, description: NrjSensor) -> None:
        super().__init__(coordinator, msisdn)
        self.entity_description = description
        self._attr_unique_id = f"{msisdn}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value(self.line or {})

    @property
    def extra_state_attributes(self):
        line = self.line or {}
        if self.entity_description.key == "data_used":
            return {
                "plan": line.get("plan_name"),
                "contract": line.get("contract"),
                "monthly_price_eur": line.get("monthly_price"),
                "roaming_used_gb": line.get("roaming_used"),
                "roaming_limit_gb": line.get("roaming_limit"),
            }
        return None
