"""Binary Sensor Entitäten für Renault Extended."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RenaultDataCoordinator


@dataclass(frozen=True)
class RenaultBinarySensorDescription(BinarySensorEntityDescription):
    """Erweiterte Binary Sensor Beschreibung."""
    true_value: Any = None   # Welcher Wert = True?
    true_fn: Any = None      # Oder: Funktion die True/False zurückgibt


BINARY_SENSOR_DESCRIPTIONS: tuple[RenaultBinarySensorDescription, ...] = (
    RenaultBinarySensorDescription(
        key="plug_status",
        name="Ladekabel eingesteckt",
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:power-plug",
        true_value=1,
    ),
    RenaultBinarySensorDescription(
        key="charging_status",
        name="Lädt gerade",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:battery-charging",
        true_fn=lambda v: float(v) == 1.0 if v is not None else False,
    ),
    RenaultBinarySensorDescription(
        key="lock_status",
        name="Fahrzeug verriegelt",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:car-door-lock",
        true_fn=lambda v: v == "locked",
    ),
    RenaultBinarySensorDescription(
        key="door_driver",
        name="Fahrertür offen",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-door",
        true_fn=lambda v: v == "open",
    ),
    RenaultBinarySensorDescription(
        key="door_passenger",
        name="Beifahrertür offen",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-door",
        true_fn=lambda v: v == "open",
    ),
    RenaultBinarySensorDescription(
        key="door_rear_left",
        name="Hintertür links offen",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-door",
        true_fn=lambda v: v == "open",
    ),
    RenaultBinarySensorDescription(
        key="door_rear_right",
        name="Hintertür rechts offen",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-door",
        true_fn=lambda v: v == "open",
    ),
    RenaultBinarySensorDescription(
        key="hatch_status",
        name="Heckklappe offen",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-back",
        true_fn=lambda v: v == "open",
    ),
    RenaultBinarySensorDescription(
        key="hvac_status",
        name="Klimaanlage aktiv",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:air-conditioner",
        true_fn=lambda v: v == "on",
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
        RenaultBinarySensor(coordinator, description, vin, vehicle_name)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class RenaultBinarySensor(CoordinatorEntity[RenaultDataCoordinator], BinarySensorEntity):
    """Einzelner Renault Binary Sensor."""

    entity_description: RenaultBinarySensorDescription

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        description: RenaultBinarySensorDescription,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._attr_unique_id = f"{vin}_binary_{description.key}"
        self._attr_name = f"{vehicle_name} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.data.get(self.entity_description.key)
        if val is None:
            return None
        fn = self.entity_description.true_fn
        if fn is not None:
            try:
                return fn(val)
            except Exception:
                return None
        return val == self.entity_description.true_value

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(self.entity_description.key) is not None
        )
