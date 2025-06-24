"""Options flow implamentation."""

import logging

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.entity_registry as er

from .const import DOMAIN
from .device_map import (
    ADAPTIVE_TRIGGERS,
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
    ATTR_TURN_OFF_ALARM_NOTIFICATION,
    ATTR_TURN_OFF_TEMPERATURE_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)


class DanthermOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        STEP_INIT_SCHEMA = vol.Schema(
            {
                vol.Optional(ATTR_BOOST_MODE_TRIGGER): str,
                vol.Optional(ATTR_ECO_MODE_TRIGGER): str,
                vol.Optional(ATTR_HOME_MODE_TRIGGER): str,
                vol.Optional(
                    ATTR_TURN_OFF_TEMPERATURE_UNKNOWN,
                    default=self.config_entry.options.get(
                        ATTR_TURN_OFF_TEMPERATURE_UNKNOWN, False
                    ),
                ): bool,
                vol.Optional(
                    ATTR_TURN_OFF_ALARM_NOTIFICATION,
                    default=self.config_entry.options.get(
                        ATTR_TURN_OFF_ALARM_NOTIFICATION, False
                    ),
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

            if not errors:
                # current_opts = self.config_entry.options or {}
                # if user_input != current_opts:
                # Persist the new options
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=user_input
                )

                # Schedule integration reload on next data update
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
                self.config_entry.options,
            ),
        )
