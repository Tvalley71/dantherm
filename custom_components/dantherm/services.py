"""Services implementation."""

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import DOMAIN
from .device_map import (
    ATTR_AWAY_MODE,
    ATTR_FAN_LEVEL_SELECTION,
    ATTR_FIREPLACE_MODE,
    ATTR_MANUAL_BYPASS_MODE,
    ATTR_OPERATION_SELECTION,
    ATTR_SUMMER_MODE,
    FAN_LEVEL_SELECTIONS,
    OPERATION_SELECTIONS,
    SERVICE_ALARM_RESET,
    SERVICE_FILTER_RESET,
    SERVICE_SET_STATE,
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


async def async_setup_services(hass: HomeAssistant):
    """Set up all services."""

    async def async_set_state(call):
        """Set state, allow combining of all control all the Dantherm control elements."""

        async def async_set_mode(device, mode, state_on, state_off):
            """Set mode."""

            state = call.data.get(mode, None)
            if state is not None:
                if state:
                    await device.set_active_unit_mode(state_on)
                else:
                    await device.set_active_unit_mode(state_off)

        config_entry_ids = await async_extract_config_entry_ids(hass, call)
        for config_entry_id in config_entry_ids:
            # Need to check if it is our config entry since async_extract_config_entry_ids
            # can return config entries from other integrations also
            # (e.g. area id or devices with entities from multiple integrations)
            if config_entry := hass.config_entries.async_get_entry(config_entry_id):
                if config_entry.domain == DOMAIN:
                    device = hass.data[DOMAIN].get(config_entry_id, None)
                    if device is None:
                        _LOGGER.error("Device %s not found", config_entry_id)
                    else:
                        operation_selection = call.data.get(
                            ATTR_OPERATION_SELECTION, None
                        )
                        if operation_selection:
                            await device.set_operation_selection(operation_selection)

                        fan_level_selection = call.data.get(
                            ATTR_FAN_LEVEL_SELECTION, None
                        )
                        if fan_level_selection:
                            await device.set_fan_level(fan_level_selection)

                        await async_set_mode(
                            device,
                            ATTR_AWAY_MODE,
                            ActiveUnitMode.StartAway,
                            ActiveUnitMode.EndAway,
                        )
                        await async_set_mode(
                            device,
                            ATTR_SUMMER_MODE,
                            ActiveUnitMode.StartSummer,
                            ActiveUnitMode.EndSummer,
                        )
                        await async_set_mode(
                            device,
                            ATTR_FIREPLACE_MODE,
                            ActiveUnitMode.StartFireplace,
                            ActiveUnitMode.EndFireplace,
                        )
                        await async_set_mode(
                            device,
                            ATTR_MANUAL_BYPASS_MODE,
                            ActiveUnitMode.SelectManualBypass,
                            ActiveUnitMode.DeselectManualBypass,
                        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_STATE,
        async_set_state,
        schema=DANTHERM_SET_STATE_SCHEMA,
    )

    async def async_filter_reset(call):
        """Filter reset, reset the filter remaining days to its filter lifetime."""

        config_entry_ids = await async_extract_config_entry_ids(hass, call)
        for config_entry_id in config_entry_ids:
            # Need to check if it is our config entry since async_extract_config_entry_ids
            # can return config entries from other integrations also
            # (e.g. area id or devices with entities from multiple integrations)
            if config_entry := hass.config_entries.async_get_entry(config_entry_id):
                if config_entry.domain == DOMAIN:
                    device = hass.data[DOMAIN].get(config_entry_id, None)
                    if device is None:
                        _LOGGER.error("Device %s not found", config_entry_id)
                    else:
                        await device.filter_reset()

    hass.services.async_register(
        DOMAIN,
        SERVICE_FILTER_RESET,
        async_filter_reset,
    )

    async def async_alarm_reset(call):
        """Alarm reset, reset first pending alarm."""

        config_entry_ids = await async_extract_config_entry_ids(hass, call)
        for config_entry_id in config_entry_ids:
            # Need to check if it is our config entry since async_extract_config_entry_ids
            # can return config entries from other integrations also
            # (e.g. area id or devices with entities from multiple integrations)
            if config_entry := hass.config_entries.async_get_entry(config_entry_id):
                if config_entry.domain == DOMAIN:
                    device = hass.data[DOMAIN].get(config_entry_id, None)
                    if device is None:
                        _LOGGER.error("Device %s not found", config_entry_id)
                    else:
                        await device.alarm_reset()

    hass.services.async_register(
        DOMAIN,
        SERVICE_ALARM_RESET,
        async_alarm_reset,
    )
