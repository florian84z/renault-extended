"""Sensor-Entitäten für Renault Extended."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHARGE_POWER_LABELS, DOMAIN, LAST_N_CHARGES
from .coordinator import RenaultDataCoordinator

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenaultSensorDescription(SensorEntityDescription):
    """Erweiterte Sensor-Beschreibung."""
    value_fn: Any = None          # Optional: Transformationsfunktion
    unit_multiplier: float = 1.0  # z.B. mbar → bar


# ── Sensor-Definitionen ───────────────────────────────────────────────────────

SENSOR_DESCRIPTIONS: tuple[RenaultSensorDescription, ...] = (

    # ── Akku ──────────────────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="battery_level",
        name="Akkustand",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    RenaultSensorDescription(
        key="battery_autonomy_km",
        name="Reichweite",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:map-marker-distance",
    ),
    RenaultSensorDescription(
        key="battery_available_energy",
        name="Verfügbare Energie",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:lightning-bolt",
    ),
    RenaultSensorDescription(
        key="battery_temperature",
        name="Akkutemperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
    ),
    RenaultSensorDescription(
        key="charging_instant_power",
        name="Ladeleistung",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:ev-station",
    ),
    RenaultSensorDescription(
        key="charging_remaining_time",
        name="Restladezeit",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer",
    ),
    RenaultSensorDescription(
        key="plug_status",
        name="Ladestecker Status",
        icon="mdi:power-plug",
        value_fn=lambda v: "Eingesteckt" if v == 1 else "Nicht eingesteckt" if v == 0 else str(v),
    ),
    RenaultSensorDescription(
        key="charging_status",
        name="Ladestatus",
        icon="mdi:battery-charging",
        value_fn=lambda v: {
            1.0: "Lädt",
            0.0: "Lädt nicht",
            -1.0: "Fehler",
        }.get(float(v) if v is not None else None, str(v)),
    ),

    # ── Kilometerstand ────────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="total_mileage",
        name="Kilometerstand",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:counter",
    ),

    # ── Letzter Ladevorgang ───────────────────────────────────────────────────
    RenaultSensorDescription(
        key="last_charge_start",
        name="Letztes Laden: Start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),
    RenaultSensorDescription(
        key="last_charge_end",
        name="Letztes Laden: Ende",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-end",
    ),
    RenaultSensorDescription(
        key="last_charge_duration_min",
        name="Letztes Laden: Dauer",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-outline",
    ),
    RenaultSensorDescription(
        key="last_charge_soc_start",
        name="Letztes Laden: SOC Start",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-arrow-down",
    ),
    RenaultSensorDescription(
        key="last_charge_soc_end",
        name="Letztes Laden: SOC Ende",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-arrow-up",
    ),
    RenaultSensorDescription(
        key="last_charge_soc_recovered",
        name="Letztes Laden: SOC Geladen",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-plus",
    ),
    RenaultSensorDescription(
        key="last_charge_power_type",
        name="Letztes Laden: Ladeart",
        icon="mdi:ev-plug-type2",
        value_fn=lambda v: CHARGE_POWER_LABELS.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="last_charge_power_w",
        name="Letztes Laden: Startleistung",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:flash",
    ),
    RenaultSensorDescription(
        key="last_charge_status",
        name="Letztes Laden: Status",
        icon="mdi:check-circle",
        value_fn=lambda v: {"ok": "Erfolgreich", "error": "Fehler"}.get(v, v) if v else None,
    ),

    # ── Ladehistorie Statistik ────────────────────────────────────────────────
    RenaultSensorDescription(
        key="charges_count",
        name="Ladevorgänge gesamt (Zeitraum)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
    ),
    RenaultSensorDescription(
        key="charge_sessions_total",
        name="Ladesessions (Zusammenfassung)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
    ),
    RenaultSensorDescription(
        key="charge_errors_total",
        name="Ladefehlschläge (Zeitraum)",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle",
    ),
    RenaultSensorDescription(
        key="charge_duration_total_h",
        name="Gesamtladezeit (Zeitraum)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:timer-sand",
    ),

    # ── HVAC ──────────────────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="hvac_status",
        name="Klimaanlage Status",
        icon="mdi:air-conditioner",
        value_fn=lambda v: {"on": "Ein", "off": "Aus"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="external_temperature",
        name="Außentemperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
    ),

    # ── Türen / Schloss ───────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="lock_status",
        name="Türschloss",
        icon="mdi:car-door-lock",
        value_fn=lambda v: {"locked": "Verriegelt", "unlocked": "Entriegelt"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="door_driver",
        name="Tür Fahrer",
        icon="mdi:car-door",
        value_fn=lambda v: {"open": "Offen", "closed": "Geschlossen"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="door_passenger",
        name="Tür Beifahrer",
        icon="mdi:car-door",
        value_fn=lambda v: {"open": "Offen", "closed": "Geschlossen"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="door_rear_left",
        name="Tür hinten links",
        icon="mdi:car-door",
        value_fn=lambda v: {"open": "Offen", "closed": "Geschlossen"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="door_rear_right",
        name="Tür hinten rechts",
        icon="mdi:car-door",
        value_fn=lambda v: {"open": "Offen", "closed": "Geschlossen"}.get(v, v) if v else None,
    ),
    RenaultSensorDescription(
        key="hatch_status",
        name="Heckklappe",
        icon="mdi:car-back",
        value_fn=lambda v: {"open": "Offen", "closed": "Geschlossen"}.get(v, v) if v else None,
    ),

    # ── Reifendruck ───────────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="tyre_fl_pressure",
        name="Reifendruck vorne links",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.MBAR,
        icon="mdi:tire",
    ),
    RenaultSensorDescription(
        key="tyre_fr_pressure",
        name="Reifendruck vorne rechts",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.MBAR,
        icon="mdi:tire",
    ),
    RenaultSensorDescription(
        key="tyre_rl_pressure",
        name="Reifendruck hinten links",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.MBAR,
        icon="mdi:tire",
    ),
    RenaultSensorDescription(
        key="tyre_rr_pressure",
        name="Reifendruck hinten rechts",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.MBAR,
        icon="mdi:tire",
    ),

    # ── Res State ─────────────────────────────────────────────────────────────
    RenaultSensorDescription(
        key="res_state_details",
        name="Remote Start Status",
        icon="mdi:remote",
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

    entities: list[RenaultSensor] = []

    # Statische Sensoren
    for description in SENSOR_DESCRIPTIONS:
        entities.append(RenaultSensor(coordinator, description, vin, vehicle_name))

    # Dynamische Sensoren für die letzten N Ladevorgänge (als Attribute)
    # Diese werden als ein einziger "Ladehistorie" Sensor mit allen Daten als Attributen gebaut
    entities.append(RenaultChargeHistorySensor(coordinator, vin, vehicle_name))

    async_add_entities(entities)


class RenaultSensor(CoordinatorEntity[RenaultDataCoordinator], SensorEntity):
    """Einzelner Renault Sensor."""

    entity_description: RenaultSensorDescription

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        description: RenaultSensorDescription,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._attr_unique_id = f"{vin}_{description.key}"
        self._attr_name = f"{vehicle_name} {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get(self.entity_description.key)
        if val is None:
            return None
        fn = self.entity_description.value_fn
        if fn is not None:
            try:
                return fn(val)
            except Exception:
                return val
        return val

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(self.entity_description.key) is not None
        )


class RenaultChargeHistorySensor(CoordinatorEntity[RenaultDataCoordinator], SensorEntity):
    """
    Sensor der die komplette Ladehistorie als Attribut-Liste enthält.
    State = Anzahl Ladevorgänge im Zeitraum.
    Attributes = alle Ladevorgänge als JSON-Liste.
    """

    def __init__(
        self,
        coordinator: RenaultDataCoordinator,
        vin: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vin = vin
        self._attr_unique_id = f"{vin}_charge_history_full"
        self._attr_name = f"{vehicle_name} Ladehistorie"
        self._attr_icon = "mdi:history"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=vehicle_name,
            manufacturer="Renault",
            model=vehicle_name,
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("charges_count")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        charges = self.coordinator.data.get("charges_raw", [])
        history = self.coordinator.data.get("charge_history_raw", [])
        return {
            "charges":         charges,
            "daily_summaries": history,
            "history_days":    self.coordinator._history_days,
            "last_updated":    self.coordinator.last_update_success,
        }
