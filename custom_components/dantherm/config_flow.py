"""Config Flow implamentation."""

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


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in [4, 6]:
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))


def host_in_configuration_exists(hass: HomeAssistant, host, entry_id=None):
    """Return True if host exists in configuration (ignore current entry in options flow)."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data[CONF_HOST] == host and entry.entry_id != entry_id:
            return True
    return False


class DanthermConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dantherm Modbus configflow."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            if host_in_configuration_exists(
                self.hass, user_input[CONF_HOST], self.config_entry.entry_id
            ):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid host IP"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ):
        """Create the options flow."""
        return DanthermOptionsFlowHandler()


class DanthermOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""

    def _get_suggested_options(self, user_input, data, options):
        """Combine user_input, data, and options for suggested values."""
        suggested = dict(options)
        suggested.update(data)
        if user_input:
            suggested.update(user_input)
        return suggested

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        options = dict(self.config_entry.options)
        data = dict(self.config_entry.data)

        STEP_INIT_SCHEMA = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=data.get(CONF_HOST, "")): str,
                vol.Optional(CONF_PORT, default=data.get(CONF_PORT, 0)): int,
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
            # Validate the user-inputted entities
            entity_registry = er.async_get(self.hass)
            for entity_key in ADAPTIVE_TRIGGERS:
                entity_id = user_input.get(entity_key)
                if entity_id and entity_id not in [
                    entity.entity_id for entity in entity_registry.entities.values()
                ]:
                    errors[entity_key] = "invalid_entity"

            # Validate host and port
            host = user_input.get(CONF_HOST)
            port = user_input.get(CONF_PORT)

            if not host:
                errors[CONF_HOST] = "required"
            elif host_in_configuration_exists(
                self.hass, host, self.config_entry.entry_id
            ):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid host IP"

            if not port:
                errors[CONF_PORT] = "required"

            if not errors:
                # Update config entry data if host or port changed
                new_data = dict(self.config_entry.data)
                if user_input[CONF_HOST] != self.config_entry.data.get(
                    CONF_HOST
                ) or user_input[CONF_PORT] != self.config_entry.data.get(CONF_PORT):
                    new_data[CONF_HOST] = user_input[CONF_HOST]
                    new_data[CONF_PORT] = user_input[CONF_PORT]
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                # Remove host/port from options before saving
                options_to_save = dict(user_input)
                options_to_save.pop(CONF_HOST, None)
                options_to_save.pop(CONF_PORT, None)

                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=options_to_save
                )

                hass_data = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                if hass_data and "coordinator" in hass_data:
                    hass_data["coordinator"].schedule_reload()

                return self.async_create_entry(title="", data=options_to_save)

            # Brug kombinerede værdier som defaults hvis der er fejl
            suggested = self._get_suggested_options(user_input, data, options)
            return self.async_show_form(
                step_id="init",
                data_schema=self.add_suggested_values_to_schema(
                    STEP_INIT_SCHEMA, suggested
                ),
                errors=errors,
            )

        # Første gang: brug data+options
        suggested = self._get_suggested_options(None, data, options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_INIT_SCHEMA, suggested
            ),
        )
