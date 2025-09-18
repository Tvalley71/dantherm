"""Services implementation."""

import logging
import re

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.event import Template
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import DOMAIN
from .device_map import (
    ATTR_AWAY_MODE,
    ATTR_BYPASS_MAXIMUM_TEMPERATURE,
    ATTR_BYPASS_MINIMUM_TEMPERATURE,
    ATTR_DISABLE_BYPASS,
    ATTR_FAN_LEVEL_SELECTION,
    ATTR_FILTER_LIFETIME,
    ATTR_FIREPLACE_MODE,
    ATTR_HUMIDITY_SETPOINT,
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
from .exceptions import InvalidTimeFormat, UnsupportedByFirmware

_LOGGER = logging.getLogger(__name__)


DANTHERM_SET_STATE_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_OPERATION_SELECTION): vol.In(OPERATION_SELECTIONS),
        vol.Optional(ATTR_FAN_LEVEL_SELECTION): vol.In(FAN_LEVEL_SELECTIONS),
        vol.Optional(ATTR_AWAY_MODE): cv.boolean,
        vol.Optional(ATTR_SUMMER_MODE): cv.boolean,
        vol.Optional(ATTR_FIREPLACE_MODE): cv.boolean,
        vol.Optional(ATTR_MANUAL_BYPASS_MODE): cv.boolean,
        vol.Optional(ATTR_DISABLE_BYPASS): cv.boolean,
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
        vol.Optional(ATTR_HUMIDITY_SETPOINT): vol.All(
            vol.Coerce(float), vol.Range(min=35, max=65)
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


async def async_setup_services(hass: HomeAssistant):  # noqa: C901
    """Set up all services."""

    def validate_time_format(time_str):
        """Validate HH:MM format."""
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
            raise InvalidTimeFormat

    def render_template(value):
        """Render a value as a template if it's a string, otherwise return it directly."""
        return (
            Template(str(value), hass).async_render()
            if isinstance(value, str)
            else value
        )

    async def async_apply_device_function(call, apply_func):
        """Extract config entries and apply function."""
        config_entry_ids = await async_extract_config_entry_ids(hass, call)
        for config_entry_id in config_entry_ids:
            config_entry = hass.config_entries.async_get_entry(config_entry_id)
            if config_entry and config_entry.domain == DOMAIN:
                entry_data = hass.data[DOMAIN].get(config_entry_id)
                if entry_data and (device := entry_data.get("device")):
                    await apply_func(device, call)
                else:
                    _LOGGER.error("Device %s not found", config_entry_id)

    async def async_set_state(call):
        """Set state for Dantherm devices."""

        async def apply_state(device, call):
            """Apply state."""

            # Apply away mode, summer mode, operation selectio, fan level selection,
            # fireplace mode, disable bypass and manual bypass mode
            if ATTR_AWAY_MODE in call.data:
                away_mode = (
                    ActiveUnitMode.StartAway
                    if bool(render_template(call.data[ATTR_AWAY_MODE]))
                    else ActiveUnitMode.EndAway
                )
                device.coordinator.enqueue_frontend(
                    device.set_active_unit_mode, away_mode
                )

            if ATTR_SUMMER_MODE in call.data:
                summer_mode = (
                    ActiveUnitMode.StartSummer
                    if bool(render_template(call.data[ATTR_SUMMER_MODE]))
                    else ActiveUnitMode.EndSummer
                )
                device.coordinator.enqueue_frontend(
                    device.set_active_unit_mode, summer_mode
                )

            if ATTR_OPERATION_SELECTION in call.data:
                operation_selection = render_template(
                    call.data[ATTR_OPERATION_SELECTION]
                )
                device.coordinator.enqueue_frontend(
                    device.set_operation_selection, operation_selection
                )

            if ATTR_FAN_LEVEL_SELECTION in call.data:
                fan_level = render_template(call.data[ATTR_FAN_LEVEL_SELECTION])
                device.coordinator.enqueue_frontend(device.set_fan_level, fan_level)

            if ATTR_FIREPLACE_MODE in call.data:
                fireplace_mode = (
                    ActiveUnitMode.StartFireplace
                    if bool(render_template(call.data[ATTR_FIREPLACE_MODE]))
                    else ActiveUnitMode.EndFireplace
                )
                device.coordinator.enqueue_frontend(
                    device.set_active_unit_mode, fireplace_mode
                )

            if ATTR_DISABLE_BYPASS in call.data:
                disable_bypass = bool(render_template(call.data[ATTR_DISABLE_BYPASS]))
                device.coordinator.enqueue_frontend(
                    device.set_disable_bypass, disable_bypass
                )

            if ATTR_MANUAL_BYPASS_MODE in call.data:
                bypass_mode = (
                    ActiveUnitMode.SelectManualBypass
                    if bool(render_template(call.data[ATTR_MANUAL_BYPASS_MODE]))
                    else ActiveUnitMode.DeselectManualBypass
                )
                device.coordinator.enqueue_frontend(
                    device.set_active_unit_mode, bypass_mode
                )

        await async_apply_device_function(call, apply_state)

    async def async_set_configuration(call):
        """Set configuration for Dantherm devices."""

        async def apply_config(device, call):
            """Apply configuration."""

            supports_write_from_2_70 = (
                getattr(device, "get_device_fw_version", 0) >= 2.70
            )

            # Check for unsupported fields and raise error if any are present
            if not supports_write_from_2_70:
                unsupported = [
                    key
                    for key in (
                        ATTR_BYPASS_MINIMUM_TEMPERATURE,
                        ATTR_BYPASS_MAXIMUM_TEMPERATURE,
                        ATTR_HUMIDITY_SETPOINT,
                        ATTR_MANUAL_BYPASS_DURATION,
                    )
                    if key in call.data
                ]
                if unsupported:
                    raise UnsupportedByFirmware(unsupported)

            # Apply bypass minimum and maximum temperature, filter lifetime,
            # manual bypass duration, night mode, night mode start and end time,
            # and week program selection
            if ATTR_BYPASS_MINIMUM_TEMPERATURE in call.data:
                bypass_minimum_temperature = float(
                    render_template(call.data[ATTR_BYPASS_MINIMUM_TEMPERATURE])
                )
                device.coordinator.enqueue_frontend(
                    device.set_bypass_minimum_temperature, bypass_minimum_temperature
                )

            if ATTR_BYPASS_MAXIMUM_TEMPERATURE in call.data:
                bypass_maximum_temperature = float(
                    render_template(call.data[ATTR_BYPASS_MAXIMUM_TEMPERATURE])
                )
                device.coordinator.enqueue_frontend(
                    device.set_bypass_maximum_temperature, bypass_maximum_temperature
                )

            if ATTR_FILTER_LIFETIME in call.data:
                filter_lifetime = int(render_template(call.data[ATTR_FILTER_LIFETIME]))
                device.coordinator.enqueue_frontend(
                    device.set_filter_lifetime, filter_lifetime
                )

            if ATTR_HUMIDITY_SETPOINT in call.data:
                humidity_setpoint = float(
                    render_template(call.data[ATTR_HUMIDITY_SETPOINT])
                )
                device.coordinator.enqueue_frontend(
                    device.set_humidity_setpoint, humidity_setpoint
                )

            if ATTR_MANUAL_BYPASS_DURATION in call.data:
                bypass_duration = int(
                    render_template(call.data[ATTR_MANUAL_BYPASS_DURATION])
                )
                device.coordinator.enqueue_frontend(
                    device.set_manual_bypass_duration, bypass_duration
                )

            if ATTR_NIGHT_MODE in call.data:
                night_mode = (
                    ActiveUnitMode.NightEnable
                    if bool(render_template(call.data[ATTR_NIGHT_MODE]))
                    else ActiveUnitMode.NightDisable
                )
                device.coordinator.enqueue_frontend(
                    device.set_active_unit_mode, night_mode
                )

            if ATTR_NIGHT_MODE_START_TIME in call.data:
                start_time = render_template(call.data[ATTR_NIGHT_MODE_START_TIME])
                validate_time_format(start_time)
                device.coordinator.enqueue_frontend(
                    device.set_night_mode_start_time, start_time
                )

            if ATTR_NIGHT_MODE_END_TIME in call.data:
                end_time = render_template(call.data[ATTR_NIGHT_MODE_END_TIME])
                validate_time_format(end_time)
                device.coordinator.enqueue_frontend(
                    device.set_night_mode_end_time, end_time
                )

            if ATTR_WEEK_PROGRAM_SELECTION in call.data:
                week_program_selection = render_template(
                    call.data[ATTR_WEEK_PROGRAM_SELECTION]
                )
                device.coordinator.enqueue_frontend(
                    device.set_week_program_selection, week_program_selection
                )

        await async_apply_device_function(call, apply_config)

    async def async_filter_reset(call):
        """Filter reset, reset the filter remaining days to its filter lifetime."""

        async def apply_reset(device, call):
            device.coordinator.write(device.filter_reset)

        await async_apply_device_function(call, apply_reset)

    async def async_alarm_reset(call):
        """Alarm reset, reset first pending alarm."""

        async def apply_reset(device, call):
            device.coordinator.write(device.alarm_reset)

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
