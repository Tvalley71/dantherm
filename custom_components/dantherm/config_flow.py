"""Config Flow implementation."""

import contextlib
import ipaddress
import logging
import os
import re
import time
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
    CONF_POLLING_SPEED,
    POLLING_OPTIONS,
    POLLING_OPTIONS_LIST,
)
from .helpers import is_primary_entry

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
)

# Debug mode configuration
# Set environment variable DANTHERM_DEBUG=1 to enable debug mode.
# In debug mode:
# - Multiple instances of the same device (same IP) can be created
# - Unique IDs are timestamped to avoid conflicts
# - Config entry titles include debug timestamp for identification
# This is useful for testing with only one physical device.
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

    VERSION = 3  # Current version of the config flow
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

            # Use default scan_interval for initial setup
            scan_interval = DEFAULT_SCAN_INTERVAL

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
                    if IS_DEBUG:
                        # In debug mode, allow multiple instances by making unique ID more unique
                        unique = f"{host}_{int(time.time() * 1000) % 100000}"  # Add timestamp suffix
                    else:
                        unique = str(device.get_device_serial_number)
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
                    # Create config entry data with numeric scan_interval
                    data = {
                        CONF_NAME: name,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SCAN_INTERVAL: scan_interval,  # Store as numeric value
                    }

                    return self.async_create_entry(title=name, data=data)
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

    def _get_polling_speed_from_interval(self, interval: int) -> str:
        """Convert scan interval to polling speed option."""
        # Check if it matches one of our standard intervals
        for speed, value in POLLING_OPTIONS.items():
            if value == interval:
                return speed

        # For custom intervals, return "custom" to preserve the value
        return "custom"

    def _has_custom_polling_interval(self) -> bool:
        """Check if user has a custom polling interval (not one of our standard options)."""
        current_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return current_interval not in POLLING_OPTIONS.values()

    def _get_polling_options_with_custom(self) -> list[str]:
        """Get polling options including current custom value if applicable."""
        options = list(POLLING_OPTIONS_LIST)

        if self._has_custom_polling_interval():
            current_interval = self.config_entry.data.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )
            options.append(f"custom ({current_interval}s)")

        return options

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the initial welcome screen with configuration overview."""
        # Check if user has already accepted disclaimer
        disclaimer_accepted = self.config_entry.options.get(
            "disclaimer_accepted", False
        )

        if disclaimer_accepted:
            # Skip init and go directly to network configuration
            return await self.async_step_network()

        if user_input is not None:
            # User accepted disclaimer, mark it and proceed to network configuration
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**self.config_entry.options, "disclaimer_accepted": True},
            )
            return await self.async_step_network()

        # Create a schema with a read-only information field
        schema = vol.Schema(
            {
                vol.Optional("continue", default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={},
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure network and polling settings."""
        errors: dict[str, str] = {}
        data = dict(self.config_entry.data)

        # Get current scan_interval and convert to polling speed option
        current_scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_polling_speed = self._get_polling_speed_from_interval(
            current_scan_interval
        )

        # Get available polling options (including custom if user has one)
        available_options = self._get_polling_options_with_custom()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_POLLING_SPEED, default=current_polling_speed): vol.In(
                    available_options
                ),
            }
        )

        if user_input is not None:
            # Validate host
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"

            if not errors:
                # Update data
                new_data = dict(self.config_entry.data)
                new_data[CONF_HOST] = user_input[CONF_HOST]
                new_data[CONF_PORT] = user_input[CONF_PORT]

                # Handle polling speed update
                polling_speed = user_input.get("polling_speed", current_polling_speed)

                # Only update scan_interval if user selected a new standard option
                if polling_speed in POLLING_OPTIONS:
                    new_data[CONF_SCAN_INTERVAL] = POLLING_OPTIONS[polling_speed]
                elif polling_speed == "custom":
                    # Keep existing custom interval
                    new_data[CONF_SCAN_INTERVAL] = current_scan_interval
                elif polling_speed.startswith("custom (") and polling_speed.endswith(
                    "s)"
                ):
                    # Keep existing custom interval (preserve current value)
                    new_data[CONF_SCAN_INTERVAL] = current_scan_interval

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                )
                # Go to next step
                return await self.async_step_triggers()

        return self.async_show_form(
            step_id="network", data_schema=schema, errors=errors
        )

    async def async_step_triggers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure adaptive mode triggers and calendar linking."""
        errors: dict[str, str] = {}
        options = dict(self.config_entry.options)

        schema_dict: dict[vol.Optional, Any] = {
            vol.Optional(
                CONF_BOOST_MODE_TRIGGER,
                default=options.get(CONF_BOOST_MODE_TRIGGER, ""),
            ): str,
            vol.Optional(
                CONF_ECO_MODE_TRIGGER, default=options.get(CONF_ECO_MODE_TRIGGER, "")
            ): str,
            vol.Optional(
                CONF_HOME_MODE_TRIGGER, default=options.get(CONF_HOME_MODE_TRIGGER, "")
            ): str,
        }

        # Only non-primary entries can choose to link to the primary calendar
        if not is_primary_entry(self.hass, self.config_entry.entry_id):
            schema_dict[
                vol.Optional(
                    CONF_LINK_TO_PRIMARY_CALENDAR,
                    default=options.get(CONF_LINK_TO_PRIMARY_CALENDAR, True),
                )
            ] = vol.Coerce(bool)

        schema = vol.Schema(schema_dict)

        if user_input is not None:
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
                # Update options
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options={**options, **user_input},
                )
                # Go to next step
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="triggers", data_schema=schema, errors=errors
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure advanced options."""
        options = dict(self.config_entry.options)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISABLE_TEMPERATURE_UNKNOWN,
                    default=options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False),
                ): bool,
                vol.Optional(
                    CONF_DISABLE_NOTIFICATIONS,
                    default=options.get(CONF_DISABLE_NOTIFICATIONS, False),
                ): bool,
            }
        )

        if user_input is not None:
            # Update options and reload
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**options, **user_input},
            )
            # Reload this entry so settings apply
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="advanced", data_schema=schema)
