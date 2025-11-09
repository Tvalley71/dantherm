"""Services implementation."""

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.template import Template

from .const import DOMAIN
from .device_map import (
    ATTR_AWAY_MODE,
    ATTR_BYPASS_MAXIMUM_TEMPERATURE,
    ATTR_BYPASS_MAXIMUM_TEMPERATURE_SUMMER,
    ATTR_BYPASS_MINIMUM_TEMPERATURE,
    ATTR_BYPASS_MINIMUM_TEMPERATURE_SUMMER,
    ATTR_DISABLE_BYPASS,
    ATTR_FAN_LEVEL_SELECTION,
    ATTR_FILTER_LIFETIME,
    ATTR_FIREPLACE_MODE,
    ATTR_HUMIDITY_SETPOINT,
    ATTR_HUMIDITY_SETPOINT_SUMMER,
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
    REQUIRED_FIRMWARE_2,
    REQUIRED_FIRMWARE_3,
    SERVICE_ALARM_RESET,
    SERVICE_CLEAR_ADAPTIVE_EVENT_STACK,
    SERVICE_FILTER_RESET,
    SERVICE_SET_CONFIGURATION,
    SERVICE_SET_CONFIGURATION_2,
    SERVICE_SET_CONFIGURATION_3,
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
    }
)

DANTHERM_SET_CONFIGURATION_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_FILTER_LIFETIME): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=360)
        ),
        vol.Optional(ATTR_NIGHT_MODE): cv.boolean,
        vol.Optional(ATTR_NIGHT_MODE_START_TIME): cv.string,
        vol.Optional(ATTR_NIGHT_MODE_END_TIME): cv.string,
        vol.Optional(ATTR_WEEK_PROGRAM_SELECTION): vol.In(WEEK_PROGRAM_SELECTIONS),
    }
)

DANTHERM_SET_CONFIGURATION_2_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_BYPASS_MINIMUM_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=12, max=15)
        ),
        vol.Optional(ATTR_BYPASS_MAXIMUM_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=21, max=27)
        ),
        vol.Optional(ATTR_HUMIDITY_SETPOINT): vol.All(
            vol.Coerce(float), vol.Range(min=35, max=65)
        ),
        vol.Optional(ATTR_MANUAL_BYPASS_DURATION): vol.All(
            vol.Coerce(int), vol.Range(min=60, max=480)
        ),
        vol.Optional(ATTR_DISABLE_BYPASS): cv.boolean,
    }
)

DANTHERM_SET_CONFIGURATION_3_SCHEMA = make_entity_service_schema(
    {
        vol.Optional(ATTR_BYPASS_MINIMUM_TEMPERATURE_SUMMER): vol.All(
            vol.Coerce(float), vol.Range(min=12, max=17)
        ),
        vol.Optional(ATTR_BYPASS_MAXIMUM_TEMPERATURE_SUMMER): vol.All(
            vol.Coerce(float), vol.Range(min=21, max=30)
        ),
        vol.Optional(ATTR_HUMIDITY_SETPOINT_SUMMER): vol.All(
            vol.Coerce(float), vol.Range(min=35, max=65)
        ),
    }
)

DANTHERM_FILTER_RESET_SCHEMA = make_entity_service_schema({})

DANTHERM_ALARM_RESET_SCHEMA = make_entity_service_schema({})

DANTHERM_CLEAR_ADAPTIVE_EVENT_STACK_SCHEMA = make_entity_service_schema({})


async def async_setup_services(hass: HomeAssistant) -> None:  # noqa: C901
    """Set up all services."""

    def validate_time_format(time_str: str) -> None:
        """Validate HH:MM format."""
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
            raise InvalidTimeFormat

    def render_template(value: Any) -> Any:
        """Render a value as a template if it's a string, otherwise return it directly."""
        return (
            Template(str(value), hass).async_render()
            if isinstance(value, str)
            else value
        )

    async def async_apply_device_function(call: ServiceCall, apply_func: Any) -> None:
        """Extract devices and apply function to each device."""
        processed_config_entries = set()

        # Get device_ids from call
        device_ids = call.data.get("device_id", [])
        if not device_ids:
            _LOGGER.error("Device_id must be specified")
            return

        device_registry = dr.async_get(hass)

        for device_id in device_ids:
            device_entry = device_registry.async_get(device_id)
            if device_entry and device_entry.config_entries:
                for config_entry_id in device_entry.config_entries:
                    if config_entry_id not in processed_config_entries:
                        processed_config_entries.add(config_entry_id)
                        config_entry = hass.config_entries.async_get_entry(
                            config_entry_id
                        )
                        if config_entry and config_entry.domain == DOMAIN:
                            entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
                            if entry_data and (device := entry_data.get("device")):
                                await apply_func(device, call)
                            else:
                                _LOGGER.error(
                                    "Device for device_id %s not found", device_id
                                )
                        else:
                            _LOGGER.debug(
                                "Device %s not from domain %s", device_id, DOMAIN
                            )
            else:
                _LOGGER.error("Device %s not found in registry", device_id)

    async def async_set_state(call: ServiceCall) -> None:
        """Set state for Dantherm devices."""

        async def apply_state(device: Any, call: ServiceCall) -> None:
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

    async def async_set_configuration(call: ServiceCall) -> None:
        """Set configuration for Dantherm devices."""

        async def apply_config(device: Any, call: ServiceCall) -> None:
            """Apply configuration."""

            # Apply filter lifetime, night mode, night mode start and end time,
            # and week program selection
            if ATTR_FILTER_LIFETIME in call.data:
                filter_lifetime = int(render_template(call.data[ATTR_FILTER_LIFETIME]))
                device.coordinator.enqueue_frontend(
                    device.set_filter_lifetime, filter_lifetime
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

    async def async_set_configuration_2(call: ServiceCall) -> None:
        """Set configuration for Dantherm devices."""

        async def apply_config_2(device: Any, call: ServiceCall) -> None:
            """Apply configuration 2."""

            # Get firmware version, default to 0 if not available
            firmware_version = getattr(device, "get_device_fw_version", 0)

            # All fields in this service are unsupported for firmware < 2.70
            if firmware_version < REQUIRED_FIRMWARE_2:
                raise UnsupportedByFirmware

            # Apply bypass minimum and maximum temperature, manual bypass duration
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

            if ATTR_DISABLE_BYPASS in call.data:
                disable_bypass = bool(render_template(call.data[ATTR_DISABLE_BYPASS]))
                device.coordinator.enqueue_frontend(
                    device.set_disable_bypass, disable_bypass
                )

        await async_apply_device_function(call, apply_config_2)

    async def async_set_configuration_3(call: ServiceCall) -> None:
        """Set configuration for Dantherm devices."""

        async def apply_config_3(device: Any, call: ServiceCall) -> None:
            """Apply configuration 3."""

            # Get firmware version, default to 0 if not available
            firmware_version = getattr(device, "get_device_fw_version", 0)

            # All fields in this service are unsupported for firmware < 3.08
            if firmware_version < REQUIRED_FIRMWARE_3:
                raise UnsupportedByFirmware

            # Apply bypass minimum and maximum temperature, manual bypass duration
            if ATTR_BYPASS_MINIMUM_TEMPERATURE_SUMMER in call.data:
                bypass_minimum_temperature_summer = float(
                    render_template(call.data[ATTR_BYPASS_MINIMUM_TEMPERATURE_SUMMER])
                )
                device.coordinator.enqueue_frontend(
                    device.set_bypass_minimum_temperature_summer,
                    bypass_minimum_temperature_summer,
                )

            if ATTR_BYPASS_MAXIMUM_TEMPERATURE_SUMMER in call.data:
                bypass_maximum_temperature_summer = float(
                    render_template(call.data[ATTR_BYPASS_MAXIMUM_TEMPERATURE_SUMMER])
                )
                device.coordinator.enqueue_frontend(
                    device.set_bypass_maximum_temperature_summer,
                    bypass_maximum_temperature_summer,
                )

            if ATTR_HUMIDITY_SETPOINT_SUMMER in call.data:
                humidity_setpoint_summer = float(
                    render_template(call.data[ATTR_HUMIDITY_SETPOINT_SUMMER])
                )
                device.coordinator.enqueue_frontend(
                    device.set_humidity_setpoint_summer, humidity_setpoint_summer
                )

        await async_apply_device_function(call, apply_config_3)

    async def async_filter_reset(call: ServiceCall) -> None:
        """Filter reset, reset the filter remaining days to its filter lifetime."""

        async def apply_reset(device: Any, call: ServiceCall) -> None:
            # Schedule the reset via the coordinator's frontend queue
            device.coordinator.enqueue_frontend(device.set_filter_reset)

        await async_apply_device_function(call, apply_reset)

    async def async_alarm_reset(call: ServiceCall) -> None:
        """Alarm reset, reset first pending alarm."""

        async def apply_reset(device: Any, call: ServiceCall) -> None:
            # Schedule the reset via the coordinator's frontend queue
            device.coordinator.enqueue_frontend(device.set_alarm_reset)

        await async_apply_device_function(call, apply_reset)

    async def async_clear_adaptive_event_stack(call: ServiceCall) -> None:
        """Clear the adaptive event stack."""

        async def apply_clear(device: Any, call: ServiceCall) -> None:
            # Schedule clear via the coordinator's frontend queue
            device.coordinator.enqueue_frontend(device.clear_adaptive_event_stack)

        await async_apply_device_function(call, apply_clear)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_STATE, async_set_state, schema=DANTHERM_SET_STATE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONFIGURATION,
        async_set_configuration,
        schema=DANTHERM_SET_CONFIGURATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONFIGURATION_2,
        async_set_configuration_2,
        schema=DANTHERM_SET_CONFIGURATION_2_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONFIGURATION_3,
        async_set_configuration_3,
        schema=DANTHERM_SET_CONFIGURATION_3_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FILTER_RESET,
        async_filter_reset,
        schema=DANTHERM_FILTER_RESET_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ALARM_RESET,
        async_alarm_reset,
        schema=DANTHERM_ALARM_RESET_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ADAPTIVE_EVENT_STACK,
        async_clear_adaptive_event_stack,
        schema=DANTHERM_CLEAR_ADAPTIVE_EVENT_STACK_SCHEMA,
    )
