"""Config Flow implamentation."""

import ipaddress
import logging
import re
from typing import Final

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.entity_registry as er

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)

ATTR_BOOST_MODE_TRIGGER: Final = "boost_mode_trigger"

ATTR_ECO_MODE_TRIGGER: Final = "eco_mode_trigger"

ATTR_HOME_MODE_TRIGGER: Final = "home_mode_trigger"


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in [4, 6]:
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))


@callback
def dantherm_modbus_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return {
        entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)
    }


class DanthermConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dantherm Modbus configflow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        if host in dantherm_modbus_entries(self.hass):
            return True
        return False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            if self._host_in_configuration_exists(host):
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
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._conf_app_id: str | None = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        STEP_INIT_SCHEMA = vol.Schema(
            {
                vol.Optional(ATTR_BOOST_MODE_TRIGGER): str,
                vol.Optional(ATTR_ECO_MODE_TRIGGER): str,
                vol.Optional(ATTR_HOME_MODE_TRIGGER): str,
            }
        )

        if user_input is not None:
            # Validate the user-inputted entities
            entity_registry = er.async_get(self.hass)
            for entity_key in [
                ATTR_BOOST_MODE_TRIGGER,
                ATTR_ECO_MODE_TRIGGER,
                ATTR_HOME_MODE_TRIGGER,
            ]:
                entity_id = user_input.get(entity_key)
                if entity_id and entity_id not in [
                    entity.entity_id for entity in entity_registry.entities.values()
                ]:
                    errors[entity_key] = "invalid_entity"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=user_input
                )

                # Get the device instance and update the triggers
                device_instance = (
                    self.hass.data.get(DOMAIN, {})
                    .get(self.config_entry.entry_id, {})
                    .get("device")
                )
                if device_instance:
                    device_instance.update_mode_triggers_event(user_input)

                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init", data_schema=STEP_INIT_SCHEMA, errors=errors
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                STEP_INIT_SCHEMA,
                self.config_entry.options,
            ),
        )
