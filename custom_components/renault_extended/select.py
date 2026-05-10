"""Select Entitäten für Renault Extended – Lademodus."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultDataCoordinator

log = logging.getLogger(__name__)

CHARGE_MODES = {
    "always":         "Immer laden",
    "always_charging": "Immer laden",
    "scheduled":      "Ladeplan",
    "schedule_mode":  "Ladeplan",
}

CHARGE_MODES_REVERSE = {v: k for k, v in CHARGE_MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    vin = entry.data["vin"]
    vehicle_name = entry.title

    async_add_entities([RenaultChargeModeSelect(coordinator, vin, vehicle_name)])


class RenaultChargeModeSelect(CoordinatorEntity[RenaultDataCoordinator], SelectEntity):
    """Lademodus auswählen."""

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vin = vin
        self._attr_unique_id = f"{vin}_charge_mode"
        self._attr_name = f"{vehicle_name} Lademodus"
        self._attr_icon = "mdi:ev-plug-type2"
        self._attr_options = ["Immer laden", "Ladeplan"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.data.get("charge_mode")
        if raw is None:
            return None
        return CHARGE_MODES.get(raw, raw)

    async def async_select_option(self, option: str) -> None:
        """Lademodus setzen."""
        # Deutschen Label zurück auf API-Wert mappen
        mode_map = {
            "Immer laden": "always",
            "Ladeplan":    "scheduled",
        }
        api_value = mode_map.get(option, "always")
        await self.coordinator.action_set_charge_mode(api_value)
        await self.coordinator.async_request_refresh()
