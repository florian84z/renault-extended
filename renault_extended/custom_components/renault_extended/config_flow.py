"""Config Flow für Renault Extended."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from renault_api.renault_client import RenaultClient

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_ACCOUNT_ID, CONF_LOCALE, CONF_VIN, DOMAIN, HISTORY_DAYS, LAST_N_CHARGES

log = logging.getLogger(__name__)

DEFAULT_LOCALE = "de_DE"


class RenaultExtendedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow für Renault Extended."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._locale: str = DEFAULT_LOCALE
        self._client: RenaultClient | None = None
        self._accounts: dict[str, str] = {}
        self._account_id: str = ""
        self._vehicles: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Schritt 1: Credentials eingeben."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._locale = user_input.get(CONF_LOCALE, DEFAULT_LOCALE)

            try:
                websession = async_get_clientsession(self.hass)
                self._client = RenaultClient(
                    websession=websession, locale=self._locale
                )
                await self._client.session.login(self._username, self._password)

                person = await self._client.get_person()
                self._accounts = {
                    acc.accountId: acc.accountId
                    for acc in (person.accounts or [])
                    if acc.accountId
                }

                if not self._accounts:
                    errors["base"] = "no_vehicles"
                elif len(self._accounts) == 1:
                    self._account_id = list(self._accounts.keys())[0]
                    return await self.async_step_vehicle()
                else:
                    return await self.async_step_account()

            except aiohttp.ClientResponseError as e:
                log.error("Renault login fehlgeschlagen: %s", e)
                errors["base"] = "invalid_credentials"
            except aiohttp.ClientConnectorError:
                errors["base"] = "cannot_connect"
            except Exception as e:  # noqa: BLE001
                log.exception("Unbekannter Fehler beim Login: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._username): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_LOCALE, default=DEFAULT_LOCALE): str,
                }
            ),
            errors=errors,
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Schritt 2: Konto wählen (nur wenn mehrere Konten vorhanden)."""
        if user_input is not None:
            self._account_id = user_input[CONF_ACCOUNT_ID]
            return await self.async_step_vehicle()

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_ID): vol.In(self._accounts),
                }
            ),
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Schritt 3: Fahrzeug wählen."""
        errors: dict[str, str] = {}

        if not self._vehicles:
            try:
                account = await self._client.get_api_account(self._account_id)
                vehicles_response = await account.get_vehicles()
                self._vehicles = {
                    v.vin: f"{v.vehicleDetails.get_brand_label()} {v.vehicleDetails.get_model_label()} ({v.vin})"
                    if v.vehicleDetails
                    else v.vin
                    for v in (vehicles_response.vehicleLinks or [])
                    if v.vin
                }
            except Exception as e:  # noqa: BLE001
                log.exception("Fehler beim Laden der Fahrzeuge: %s", e)
                errors["base"] = "unknown"

        if not self._vehicles:
            errors["base"] = "no_vehicles"

        if user_input is not None and not errors:
            vin = user_input[CONF_VIN]

            await self.async_set_unique_id(vin)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._vehicles.get(vin, vin),
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_LOCALE: self._locale,
                    CONF_ACCOUNT_ID: self._account_id,
                    CONF_VIN: vin,
                },
            )

        if len(self._vehicles) == 1 and not errors:
            vin = list(self._vehicles.keys())[0]
            await self.async_set_unique_id(vin)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._vehicles.get(vin, vin),
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_LOCALE: self._locale,
                    CONF_ACCOUNT_ID: self._account_id,
                    CONF_VIN: vin,
                },
            )

        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VIN): vol.In(self._vehicles),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RenaultExtendedOptionsFlow:
        return RenaultExtendedOptionsFlow(config_entry)


class RenaultExtendedOptionsFlow(config_entries.OptionsFlow):
    """Options Flow für nachträgliche Einstellungen."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "history_days",
                        default=self.config_entry.options.get("history_days", HISTORY_DAYS),
                    ): vol.All(int, vol.Range(min=7, max=365)),
                    vol.Optional(
                        "last_n_charges",
                        default=self.config_entry.options.get("last_n_charges", LAST_N_CHARGES),
                    ): vol.All(int, vol.Range(min=1, max=50)),
                }
            ),
        )
