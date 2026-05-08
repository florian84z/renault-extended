"""DataUpdateCoordinator für Renault Extended."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from renault_api.renault_client import RenaultClient
from renault_api.renault_vehicle import RenaultVehicle

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    HISTORY_DAYS,
    LAST_N_CHARGES,
    SCAN_INTERVAL_HISTORY,
    SCAN_INTERVAL_REALTIME,
    SCAN_INTERVAL_STATIC,
)

log = logging.getLogger(__name__)


class RenaultDataCoordinator(DataUpdateCoordinator):
    """
    Koordiniert alle API-Aufrufe an die Renault Kamereon API.
    Teilt die Endpunkte in drei Gruppen mit unterschiedlichen Poll-Intervallen:
      - realtime:  alle 5 min  (Akku, Laden, GPS, HVAC)
      - history:   alle 6 h    (Ladehistorie, Kilometerstand)
      - static:    alle 24 h   (Reifendruck, Res-State, Lock)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        locale: str,
        account_id: str,
        vin: str,
        history_days: int = HISTORY_DAYS,
        last_n_charges: int = LAST_N_CHARGES,
    ) -> None:
        super().__init__(
            hass,
            log,
            name=f"{DOMAIN}_{vin}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_REALTIME),
        )
        self._username = username
        self._password = password
        self._locale = locale
        self._account_id = account_id
        self._vin = vin
        self._history_days = history_days
        self._last_n_charges = last_n_charges

        self._client: RenaultClient | None = None
        self._vehicle: RenaultVehicle | None = None

        self._last_history_update: datetime | None = None
        self._last_static_update: datetime | None = None

        self._history_data: dict[str, Any] = {}
        self._static_data: dict[str, Any] = {}

    # ── Login / Fahrzeug-Handle ───────────────────────────────────────────────

    async def _ensure_vehicle(self) -> RenaultVehicle:
        if self._vehicle is not None:
            return self._vehicle
        websession = async_get_clientsession(self.hass)
        self._client = RenaultClient(websession=websession, locale=self._locale)
        await self._client.session.login(self._username, self._password)
        account = await self._client.get_api_account(self._account_id)
        self._vehicle = await account.get_api_vehicle(self._vin)
        log.info("Renault Extended: Verbunden mit Fahrzeug %s", self._vin)
        return self._vehicle

    @staticmethod
    def _safe_get(obj: Any, *attrs: str, default: Any = None) -> Any:
        current = obj
        for attr in attrs:
            if current is None:
                return default
            current = getattr(current, attr, None)
        return current if current is not None else default

    def _needs_history_update(self) -> bool:
        if self._last_history_update is None:
            return True
        age = (datetime.now(timezone.utc) - self._last_history_update).total_seconds()
        return age >= SCAN_INTERVAL_HISTORY

    def _needs_static_update(self) -> bool:
        if self._last_static_update is None:
            return True
        age = (datetime.now(timezone.utc) - self._last_static_update).total_seconds()
        return age >= SCAN_INTERVAL_STATIC

    # ── Realtime Endpunkte ────────────────────────────────────────────────────

    async def _fetch_battery_status(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_battery_status()
            return {
                "battery_level":           self._safe_get(data, "batteryLevel"),
                "battery_temperature":     self._safe_get(data, "batteryTemperature"),
                "battery_autonomy_km":     self._safe_get(data, "batteryAutonomy"),
                "battery_available_energy": self._safe_get(data, "batteryAvailableEnergy"),
                "plug_status":             self._safe_get(data, "plugStatus"),
                "charging_status":         self._safe_get(data, "chargingStatus"),
                "charging_remaining_time": self._safe_get(data, "chargingRemainingTime"),
                "charging_instant_power":  self._safe_get(data, "chargingInstantaneousPower"),
                "timestamp":               self._safe_get(data, "timestamp"),
            }
        except Exception as e:
            log.warning("battery-status fehlgeschlagen: %s", e)
            return {}

    async def _fetch_location(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_location()
            return {
                "gps_latitude":     self._safe_get(data, "gpsLatitude"),
                "gps_longitude":    self._safe_get(data, "gpsLongitude"),
                "gps_direction":    self._safe_get(data, "gpsDirection"),
                "location_updated": self._safe_get(data, "lastUpdateTime"),
            }
        except Exception as e:
            log.warning("location fehlgeschlagen: %s", e)
            return {}

    async def _fetch_hvac_status(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_hvac_status()
            return {
                "hvac_status":          self._safe_get(data, "hvacStatus"),
                "external_temperature": self._safe_get(data, "externalTemperature"),
                "soc_threshold":        self._safe_get(data, "socThreshold"),
                "hvac_updated":         self._safe_get(data, "lastUpdateTime"),
            }
        except Exception as e:
            log.warning("hvac-status fehlgeschlagen: %s", e)
            return {}

    # ── History Endpunkte ─────────────────────────────────────────────────────

    async def _fetch_cockpit(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_cockpit()
            return {
                "total_mileage": self._safe_get(data, "totalMileage"),
            }
        except Exception as e:
            log.warning("cockpit fehlgeschlagen: %s", e)
            return {}

    async def _fetch_charges(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            start = datetime.now(timezone.utc) - timedelta(days=self._history_days)
            end   = datetime.now(timezone.utc)
            data  = await vehicle.get_charges(start=start, end=end)

            raw_charges = []
            if hasattr(data, "charges") and data.charges:
                raw_charges = [
                    {
                        "chargeStartDate":               getattr(c, "chargeStartDate", None),
                        "chargeEndDate":                 getattr(c, "chargeEndDate", None),
                        "chargeDuration":                getattr(c, "chargeDuration", None),
                        "chargeStartBatteryLevel":       getattr(c, "chargeStartBatteryLevel", None),
                        "chargeEndBatteryLevel":         getattr(c, "chargeEndBatteryLevel", None),
                        "chargeBatteryLevelRecovered":   getattr(c, "chargeBatteryLevelRecovered", None),
                        "chargePower":                   getattr(c, "chargePower", None),
                        "chargeStartInstantaneousPower": getattr(c, "chargeStartInstantaneousPower", None),
                        "chargeEndStatus":               getattr(c, "chargeEndStatus", None),
                    }
                    for c in data.charges
                ]

            raw_charges.sort(
                key=lambda x: x.get("chargeStartDate", "") or "", reverse=True
            )

            result: dict[str, Any] = {
                "charges_raw":   raw_charges,
                "charges_count": len(raw_charges),
            }

            for i, charge in enumerate(raw_charges[: self._last_n_charges]):
                prefix = f"charge_{i:02d}"
                result[f"{prefix}_start"]         = charge.get("chargeStartDate")
                result[f"{prefix}_end"]           = charge.get("chargeEndDate")
                result[f"{prefix}_duration_min"]  = charge.get("chargeDuration")
                result[f"{prefix}_soc_start"]     = charge.get("chargeStartBatteryLevel")
                result[f"{prefix}_soc_end"]       = charge.get("chargeEndBatteryLevel")
                result[f"{prefix}_soc_recovered"] = charge.get("chargeBatteryLevelRecovered")
                result[f"{prefix}_power_type"]    = charge.get("chargePower")
                result[f"{prefix}_power_w"]       = charge.get("chargeStartInstantaneousPower")
                result[f"{prefix}_status"]        = charge.get("chargeEndStatus")

            if raw_charges:
                last = raw_charges[0]
                result["last_charge_start"]         = last.get("chargeStartDate")
                result["last_charge_end"]           = last.get("chargeEndDate")
                result["last_charge_duration_min"]  = last.get("chargeDuration")
                result["last_charge_soc_start"]     = last.get("chargeStartBatteryLevel")
                result["last_charge_soc_end"]       = last.get("chargeEndBatteryLevel")
                result["last_charge_soc_recovered"] = last.get("chargeBatteryLevelRecovered")
                result["last_charge_power_type"]    = last.get("chargePower")
                result["last_charge_power_w"]       = last.get("chargeStartInstantaneousPower")
                result["last_charge_status"]        = last.get("chargeEndStatus")

            return result

        except Exception as e:
            log.warning("charges fehlgeschlagen: %s", e)
            return {}

    async def _fetch_charge_history(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            start = datetime.now(timezone.utc) - timedelta(days=self._history_days)
            end   = datetime.now(timezone.utc)
            # period="day" ist Pflichtparameter
            data  = await vehicle.get_charge_history(start=start, end=end, period="day")

            summaries = []
            if hasattr(data, "chargeSummaries") and data.chargeSummaries:
                summaries = [
                    {
                        "day":                  getattr(s, "day", None),
                        "totalChargesNumber":   getattr(s, "totalChargesNumber", 0),
                        "totalChargesDuration": getattr(s, "totalChargesDuration", 0),
                        "totalChargesErrors":   getattr(s, "totalChargesErrors", 0),
                    }
                    for s in data.chargeSummaries
                ]

            summaries.sort(key=lambda x: x.get("day", ""), reverse=True)

            total_sessions = sum(s.get("totalChargesNumber", 0) for s in summaries)
            total_errors   = sum(s.get("totalChargesErrors", 0) for s in summaries)
            total_duration = sum(s.get("totalChargesDuration", 0) for s in summaries)

            return {
                "charge_history_raw":      summaries,
                "charge_sessions_total":   total_sessions,
                "charge_errors_total":     total_errors,
                "charge_duration_total_h": round(total_duration / 60, 1) if total_duration else 0,
            }
        except Exception as e:
            log.warning("charge-history fehlgeschlagen: %s", e)
            return {}

    # ── Static Endpunkte (werden bei nicht-unterstützten Modellen still ignoriert) ──

    async def _fetch_lock_status(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_lock_status()
            return {
                "lock_status":   self._safe_get(data, "lockStatus"),
                "door_driver":   self._safe_get(data, "doorStatusDriver"),
                "door_passenger": self._safe_get(data, "doorStatusPassenger"),
                "door_rear_left": self._safe_get(data, "doorStatusRearLeft"),
                "door_rear_right": self._safe_get(data, "doorStatusRearRight"),
                "hatch_status":  self._safe_get(data, "hatchStatus"),
                "lock_updated":  self._safe_get(data, "lastUpdateTime"),
            }
        except Exception as e:
            log.debug("lock-status nicht verfügbar: %s", e)
            return {}

    async def _fetch_pressure(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_tyre_pressure()
            return {
                "tyre_fl_pressure": self._safe_get(data, "flPressure"),
                "tyre_fr_pressure": self._safe_get(data, "frPressure"),
                "tyre_rl_pressure": self._safe_get(data, "rlPressure"),
                "tyre_rr_pressure": self._safe_get(data, "rrPressure"),
                "tyre_fl_status":   self._safe_get(data, "flStatus"),
                "tyre_fr_status":   self._safe_get(data, "frStatus"),
                "tyre_rl_status":   self._safe_get(data, "rlStatus"),
                "tyre_rr_status":   self._safe_get(data, "rrStatus"),
            }
        except Exception as e:
            log.debug("pressure nicht verfügbar: %s", e)
            return {}

    async def _fetch_res_state(self, vehicle: RenaultVehicle) -> dict[str, Any]:
        try:
            data = await vehicle.get_res_state()
            return {
                "res_state_code":    self._safe_get(data, "code"),
                "res_state_details": self._safe_get(data, "details"),
            }
        except Exception as e:
            log.debug("res-state nicht verfügbar: %s", e)
            return {}

    # ── Hauptupdate ───────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            vehicle = await self._ensure_vehicle()
        except Exception as e:
            self._vehicle = None
            self._client = None
            raise UpdateFailed(f"Renault Login fehlgeschlagen: {e}") from e

        result: dict[str, Any] = {}

        # ── Realtime (jedes Mal) ──────────────────────────────────────────────
        realtime_results = await asyncio.gather(
            self._fetch_battery_status(vehicle),
            self._fetch_location(vehicle),
            self._fetch_hvac_status(vehicle),
            return_exceptions=True,
        )
        for res in realtime_results:
            if isinstance(res, dict):
                result.update(res)

        # ── History (alle 6 Stunden) ──────────────────────────────────────────
        if self._needs_history_update():
            log.debug("Renault Extended: Fetching history data...")
            history_results = await asyncio.gather(
                self._fetch_cockpit(vehicle),
                self._fetch_charges(vehicle),
                self._fetch_charge_history(vehicle),
                return_exceptions=True,
            )
            new_history: dict[str, Any] = {}
            for res in history_results:
                if isinstance(res, dict):
                    new_history.update(res)
            if new_history:
                self._history_data = new_history
                self._last_history_update = datetime.now(timezone.utc)

        result.update(self._history_data)

        # ── Static (alle 24 Stunden) ──────────────────────────────────────────
        if self._needs_static_update():
            log.debug("Renault Extended: Fetching static data...")
            static_results = await asyncio.gather(
                self._fetch_lock_status(vehicle),
                self._fetch_pressure(vehicle),
                self._fetch_res_state(vehicle),
                return_exceptions=True,
            )
            new_static: dict[str, Any] = {}
            for res in static_results:
                if isinstance(res, dict):
                    new_static.update(res)
            if new_static:
                self._static_data = new_static
                self._last_static_update = datetime.now(timezone.utc)

        result.update(self._static_data)

        log.debug("Renault Extended: Update abgeschlossen, %d Datenpunkte", len(result))
        return result
