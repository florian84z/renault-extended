"""Device Tracker für Renault Extended – GPS Position."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultDataCoordinator

log = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RenaultDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    vin = entry.data["vin"]
    vehicle_name = entry.title
    async_add_entities([RenaultDeviceTracker(coordinator, vin, vehicle_name)])


class RenaultDeviceTracker(CoordinatorEntity[RenaultDataCoordinator], TrackerEntity):
    """GPS-Position des Fahrzeugs."""

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vin = vin
        self._attr_unique_id = f"{vin}_location"
        self._attr_name = f"{vehicle_name} Position"
        self._attr_icon = "mdi:car-connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.coordinator.data.get("gps_latitude")

    @property
    def longitude(self) -> float | None:
        return self.coordinator.data.get("gps_longitude")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "direction":    self.coordinator.data.get("gps_direction"),
            "last_updated": self.coordinator.data.get("location_updated"),
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("gps_latitude") is not None
            and self.coordinator.data.get("gps_longitude") is not None
        )
