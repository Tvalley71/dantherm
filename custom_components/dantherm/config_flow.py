"""Config Flow implementation."""

import contextlib
import ipaddress
import logging
import os
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import DanthermDevice
from .device_map import (
    ADAPTIVE_TRIGGERS,
    CONF_BOOST_MODE_TRIGGER,
    CONF_DISABLE_NOTIFICATIONS,
    CONF_DISABLE_TEMPERATURE_UNKNOWN,
    CONF_ECO_MODE_TRIGGER,
    CONF_HOME_MODE_TRIGGER,
    CONF_LINK_TO_PRIMARY_CALENDAR,
)
from .helpers import is_primary_entry

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)

# This is used to determine if the debug mode is enabled.
IS_DEBUG = os.getenv("DANTHERM_DEBUG") == "1"

_LOGGER = logging.getLogger(__name__)


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in [4, 6]:
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))
    return False


@callback
def dantherm_modbus_entries(hass: HomeAssistant) -> set[str]:
    """Return the hosts already configured."""
    return {
        entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)
    }


class DanthermConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dantherm Modbus configflow."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _host_in_configuration_exists(self, host: str) -> bool:
        """Return True if host exists in configuration."""
        if IS_DEBUG:
            return False  # Allow duplicates in debug mode
        return host in dantherm_modbus_entries(self.hass)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input[CONF_NAME]
            port = user_input[CONF_PORT]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                # Test connection and determine unique id (serial) when not in debug mode
                device: DanthermDevice | None = None
                try:
                    device = DanthermDevice(
                        self.hass, name, host, port, 1, scan_interval, None
                    )
                    await device.async_init_and_connect()

                    # Prefer serial as config entry unique id to avoid duplicates across IP changes
                    unique = host if IS_DEBUG else str(device.get_device_serial_number)
                    await self.async_set_unique_id(unique)
                    self._abort_if_unique_id_configured()
                except Exception:
                    _LOGGER.exception("Failed to connect during config flow")
                    errors["base"] = "cannot_connect"
                finally:
                    if device is not None:
                        with contextlib.suppress(Exception):
                            await device.disconnect_and_close()

                if not errors:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )
        # Show the form on initial load or when there are errors
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "DanthermOptionsFlowHandler":
        """Create the options flow."""
        return DanthermOptionsFlowHandler(config_entry)


class DanthermOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Dantherm options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options for Dantherm."""
        errors: dict[str, str] = {}

        data = dict(self.config_entry.data)
        options = dict(self.config_entry.options)

        # Build schema - simple string fields WITHOUT defaults for triggers
        base_schema: dict = {
            vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Optional(CONF_BOOST_MODE_TRIGGER): str,
            vol.Optional(CONF_ECO_MODE_TRIGGER): str,
            vol.Optional(CONF_HOME_MODE_TRIGGER): str,
            vol.Optional(
                CONF_DISABLE_TEMPERATURE_UNKNOWN,
                default=options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False),
            ): bool,
            vol.Optional(
                CONF_DISABLE_NOTIFICATIONS,
                default=options.get(CONF_DISABLE_NOTIFICATIONS, False),
            ): bool,
        }

        # Only non-primary entries can choose to link to the primary calendar
        if not is_primary_entry(self.hass, self.config_entry.entry_id):
            base_schema[
                vol.Optional(
                    CONF_LINK_TO_PRIMARY_CALENDAR,
                    default=options.get(CONF_LINK_TO_PRIMARY_CALENDAR, True),
                )
            ] = bool

        step_schema = vol.Schema(base_schema)

        if user_input is not None:
            # Validate host
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"

            # Validate entity ids for adaptive triggers if provided
            entity_registry = er.async_get(self.hass)
            for entity_key in ADAPTIVE_TRIGGERS:
                entity_id = user_input.get(entity_key, "")

                # Handle None values and strip whitespace
                if entity_id is None:
                    entity_id = ""
                else:
                    entity_id = str(entity_id).strip()

                # Update user_input with cleaned value
                user_input[entity_key] = entity_id

                # Only validate non-empty entity IDs
                if entity_id:
                    if entity_id not in [
                        entity.entity_id for entity in entity_registry.entities.values()
                    ]:
                        errors[entity_key] = "invalid_entity"

            if not errors:
                # Update data and options
                new_data = dict(self.config_entry.data)
                new_data[CONF_HOST] = user_input.pop(CONF_HOST, new_data.get(CONF_HOST))
                new_data[CONF_PORT] = user_input.pop(
                    CONF_PORT, new_data.get(CONF_PORT, DEFAULT_PORT)
                )

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                    options=user_input,
                )
                # Reload this entry so calendar linkage and settings apply
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init", data_schema=step_schema, errors=errors
            )

        # Prepare suggested values - only include non-empty trigger values
        suggested_values = {**data}

        # Only add trigger values if they're not empty
        for trigger_key in [
            CONF_BOOST_MODE_TRIGGER,
            CONF_ECO_MODE_TRIGGER,
            CONF_HOME_MODE_TRIGGER,
        ]:
            trigger_value = options.get(trigger_key, "")
            if trigger_value:  # Only add if not empty
                suggested_values[trigger_key] = trigger_value

        # Add boolean options with defaults
        suggested_values[CONF_DISABLE_TEMPERATURE_UNKNOWN] = options.get(
            CONF_DISABLE_TEMPERATURE_UNKNOWN, False
        )
        suggested_values[CONF_DISABLE_NOTIFICATIONS] = options.get(
            CONF_DISABLE_NOTIFICATIONS, False
        )

        # Add calendar link option if not primary
        if not is_primary_entry(self.hass, self.config_entry.entry_id):
            suggested_values[CONF_LINK_TO_PRIMARY_CALENDAR] = options.get(
                CONF_LINK_TO_PRIMARY_CALENDAR, True
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                step_schema, suggested_values
            ),
        )
