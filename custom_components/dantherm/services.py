"""Services implementation."""

import logging
import re

import voluptuous as vol

from homeassistant.components.sensor import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import DOMAIN
from .device_map import (
    ATTR_AWAY_MODE,
    ATTR_BYPASS_MAXIMUM_TEMPERATURE,
    ATTR_BYPASS_MINIMUM_TEMPERATURE,
    ATTR_FAN_LEVEL_SELECTION,
    ATTR_FILTER_LIFETIME,
    ATTR_FIREPLACE_MODE,
    ATTR_MANUAL_BYPASS_DURATION,
    ATTR_MANUAL_BYPASS_MODE,
    ATTR_NIGHT_MODE,
    ATTR_NIGHT_MODE_END_TIME,
    ATTR_NIGHT_MODE_START_TIME,
    ATTR_OPERATION_SELECTION,
    ATTR_SUMMER_MODE,
    ATTR_WEEK_PROGRAM_SELECTION,
    FAN_LEVEL_SELECTIONS,
    OPERATION_SELECTIONS,
    SERVICE_ALARM_RESET,
    SERVICE_FILTER_RESET,
    SERVICE_SET_CONFIGURATION,
    SERVICE_SET_STATE,
    WEEK_PROGRAM_SELECTIONS,
    ActiveUnitMode,
)

_LOGGER = logging.getLogger(__name__)


DANTHERM_SET_STATE_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_OPERATION_SELECTION): vol.In(OPERATION_SELECTIONS),
        vol.Optional(ATTR_FAN_LEVEL_SELECTION): vol.In(FAN_LEVEL_SELECTIONS),
        vol.Optional(ATTR_AWAY_MODE): cv.boolean,
        vol.Optional(ATTR_SUMMER_MODE): cv.boolean,
        vol.Optional(ATTR_FIREPLACE_MODE): cv.boolean,
        vol.Optional(ATTR_MANUAL_BYPASS_MODE): cv.boolean,
    }
)

DANTHERM_SET_CONFIGURATION_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_BYPASS_MINIMUM_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=12, max=15)
        ),
        vol.Optional(ATTR_BYPASS_MAXIMUM_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=21, max=27)
        ),
        vol.Optional(ATTR_FILTER_LIFETIME): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=360)
        ),
        vol.Optional(ATTR_MANUAL_BYPASS_DURATION): vol.All(
            vol.Coerce(int), vol.Range(min=60, max=480)
        ),
        vol.Optional(ATTR_NIGHT_MODE): cv.boolean,
        vol.Optional(ATTR_NIGHT_MODE_START_TIME): cv.string,
        vol.Optional(ATTR_NIGHT_MODE_END_TIME): cv.string,
        vol.Optional(ATTR_WEEK_PROGRAM_SELECTION): vol.In(WEEK_PROGRAM_SELECTIONS),
    }
)


async def async_setup_services(hass: HomeAssistant):
    """Set up all services."""

    def validate_time_format(time_str):
        """Validate HH:MM format."""
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_timeformat"
            )

    async def async_apply_device_function(call, apply_func):
        """Extract config entries and apply function."""
        config_entry_ids = await async_extract_config_entry_ids(hass, call)
        for config_entry_id in config_entry_ids:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry and config_entry.domain == DOMAIN:
                device = hass.data[DOMAIN].get(config_entry_id)
                if device:
                    await apply_func(device, call)
                else:
                    _LOGGER.error("Device %s not found", config_entry_id)

    async def async_set_state(call):
        """Set state for Dantherm devices."""

        async def apply_state(device, call):
            if ATTR_OPERATION_SELECTION in call.data:
                await device.set_operation_selection(
                    call.data[ATTR_OPERATION_SELECTION]
                )
            if ATTR_FAN_LEVEL_SELECTION in call.data:
                await device.set_fan_level(call.data[ATTR_FAN_LEVEL_SELECTION])
            if ATTR_AWAY_MODE in call.data:
                await device.set_active_unit_mode(
                    ActiveUnitMode.StartAway
                    if call.data[ATTR_AWAY_MODE]
                    else ActiveUnitMode.EndAway
                )
            if ATTR_SUMMER_MODE in call.data:
                await device.set_active_unit_mode(
                    ActiveUnitMode.StartSummer
                    if call.data[ATTR_SUMMER_MODE]
                    else ActiveUnitMode.EndSummer
                )
            if ATTR_FIREPLACE_MODE in call.data:
                await device.set_active_unit_mode(
                    ActiveUnitMode.StartFireplace
                    if call.data[ATTR_FIREPLACE_MODE]
                    else ActiveUnitMode.EndFireplace
                )
            if ATTR_MANUAL_BYPASS_MODE in call.data:
                await device.set_active_unit_mode(
                    ActiveUnitMode.SelectManualBypass
                    if call.data[ATTR_MANUAL_BYPASS_MODE]
                    else ActiveUnitMode.DeselectManualBypass
                )

        await async_apply_device_function(call, apply_state)

    async def async_set_configuration(call):
        """Set configuration for Dantherm devices."""

        async def apply_config(device, call):
            if ATTR_BYPASS_MINIMUM_TEMPERATURE in call.data:
                await device.set_bypass_minimum_temperature(
                    call.data[ATTR_BYPASS_MINIMUM_TEMPERATURE]
                )
            if ATTR_BYPASS_MAXIMUM_TEMPERATURE in call.data:
                await device.set_bypass_maximum_temperature(
                    call.data[ATTR_BYPASS_MAXIMUM_TEMPERATURE]
                )
            if ATTR_FILTER_LIFETIME in call.data:
                await device.set_filter_lifetime(call.data[ATTR_FILTER_LIFETIME])
            if ATTR_MANUAL_BYPASS_DURATION in call.data:
                await device.set_manual_bypass_duration(
                    call.data[ATTR_MANUAL_BYPASS_DURATION]
                )
            if ATTR_NIGHT_MODE in call.data:
                await device.set_active_unit_mode(
                    ActiveUnitMode.NightEnable
                    if call.data[ATTR_NIGHT_MODE]
                    else ActiveUnitMode.NightDisable
                )
            if ATTR_NIGHT_MODE_START_TIME in call.data:
                validate_time_format(call.data[ATTR_NIGHT_MODE_START_TIME])
                await device.set_night_mode_start_time(
                    call.data[ATTR_NIGHT_MODE_START_TIME]
                )
            if ATTR_NIGHT_MODE_END_TIME in call.data:
                validate_time_format(call.data[ATTR_NIGHT_MODE_END_TIME])
                await device.set_night_mode_end_time(
                    call.data[ATTR_NIGHT_MODE_END_TIME]
                )
            if ATTR_WEEK_PROGRAM_SELECTION in call.data:
                await device.set_week_program_selection(
                    call.data[ATTR_WEEK_PROGRAM_SELECTION]
                )

        await async_apply_device_function(call, apply_config)

    async def async_filter_reset(call):
        """Filter reset, reset the filter remaining days to it's filter lifetime."""

        async def apply_reset(device, call):
            await device.filter_reset()

        await async_apply_device_function(call, apply_reset)

    async def async_alarm_reset(call):
        """Alarm reset, reset first pending alarm."""

        async def apply_reset(device, call):
            await device.alarm_reset()

        await async_apply_device_function(call, apply_reset)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_STATE, async_set_state, schema=DANTHERM_SET_STATE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONFIGURATION,
        async_set_configuration,
        schema=DANTHERM_SET_CONFIGURATION_SCHEMA,
    )
    hass.services.async_register(DOMAIN, SERVICE_FILTER_RESET, async_filter_reset)
    hass.services.async_register(DOMAIN, SERVICE_ALARM_RESET, async_alarm_reset)
