"""Renault Extended – Custom Integration für Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCOUNT_ID,
    CONF_LOCALE,
    CONF_VIN,
    DOMAIN,
    HISTORY_DAYS,
    LAST_N_CHARGES,
)
from .coordinator import RenaultDataCoordinator

log = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration einrichten wenn Config Entry geladen wird."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = RenaultDataCoordinator(
        hass=hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        locale=entry.data.get(CONF_LOCALE, "de_DE"),
        account_id=entry.data[CONF_ACCOUNT_ID],
        vin=entry.data[CONF_VIN],
        history_days=entry.options.get("history_days", HISTORY_DAYS),
        last_n_charges=entry.options.get("last_n_charges", LAST_N_CHARGES),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Integration neu laden wenn Options geändert wurden."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
