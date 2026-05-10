"""Button Entitäten für Renault Extended – Laden starten, HVAC etc."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultDataCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenaultButtonDescription(ButtonEntityDescription):
    """Erweiterte Button-Beschreibung."""
    action: str = ""  # Name der Coordinator-Methode


BUTTON_DESCRIPTIONS: tuple[RenaultButtonDescription, ...] = (
    RenaultButtonDescription(
        key="charge_start",
        name="Laden starten",
        icon="mdi:ev-station",
        action="action_charge_start",
    ),
    RenaultButtonDescription(
        key="hvac_start",
        name="Klimaanlage starten",
        icon="mdi:air-conditioner",
        action="action_hvac_start",
    ),
    RenaultButtonDescription(
        key="hvac_stop",
        name="Klimaanlage stoppen",
        icon="mdi:air-conditioner-off",
        action="action_hvac_stop",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    vin = entry.data["vin"]
    vehicle_name = entry.title

    async_add_entities(
        RenaultButton(coordinator, description, vin, vehicle_name)
        for description in BUTTON_DESCRIPTIONS
    )


class RenaultButton(CoordinatorEntity[RenaultDataCoordinator], ButtonEntity):
    """Renault Action Button."""

    entity_description: RenaultButtonDescription

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        description: RenaultButtonDescription,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._attr_unique_id = f"{vin}_btn_{description.key}"
        self._attr_name = f"{vehicle_name} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    async def async_press(self) -> None:
        """Button gedrückt – Action im Coordinator ausführen."""
        action = getattr(self.coordinator, self.entity_description.action, None)
        if action:
            await action()
        else:
            log.error("Unbekannte Action: %s", self.entity_description.action)
