"""Config Flow implementation."""

import ipaddress
import re

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.entity_registry as er

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .device_map import (
    ADAPTIVE_TRIGGERS,
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_DISABLE_NOTIFICATIONS,
    ATTR_DISABLE_TEMPERATURE_UNKNOWN,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


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
def dantherm_modbus_entries(hass: HomeAssistant):
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
        return host in dantherm_modbus_entries(self.hass)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Create the options flow."""
        return DanthermOptionsFlowHandler(config_entry)


class DanthermOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        options = dict(self.config_entry.options)
        data = dict(self.config_entry.data)

        STEP_INIT_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_HOST, default=data.get(CONF_HOST)): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(ATTR_BOOST_MODE_TRIGGER): str,
                vol.Optional(ATTR_ECO_MODE_TRIGGER): str,
                vol.Optional(ATTR_HOME_MODE_TRIGGER): str,
                vol.Optional(
                    ATTR_DISABLE_TEMPERATURE_UNKNOWN,
                    default=options.get(ATTR_DISABLE_TEMPERATURE_UNKNOWN, False),
                ): bool,
                vol.Optional(
                    ATTR_DISABLE_NOTIFICATIONS,
                    default=options.get(ATTR_DISABLE_NOTIFICATIONS, False),
                ): bool,
            }
        )

        if user_input is not None:
            # Validate host
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"

            # Validate entities
            entity_registry = er.async_get(self.hass)
            for entity_key in ADAPTIVE_TRIGGERS:
                entity_id = user_input.get(entity_key)
                if entity_id and entity_id not in [
                    entity.entity_id for entity in entity_registry.entities.values()
                ]:
                    errors[entity_key] = "invalid_entity"

            if not errors:
                # Update data (host + port) and options (other settings)
                new_data = dict(self.config_entry.data)
                new_data[CONF_HOST] = user_input.pop(CONF_HOST, new_data[CONF_HOST])
                new_data[CONF_PORT] = user_input.pop(CONF_PORT, new_data[CONF_PORT])

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                    options=user_input,
                )

                hass_data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                if hass_data and "coordinator" in hass_data:
                    hass_data["coordinator"].schedule_reload()

                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init", data_schema=STEP_INIT_SCHEMA, errors=errors
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_INIT_SCHEMA,
                {**data, **options},  # Prefill with both data + options
            ),
        )
