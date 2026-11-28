"""Climate implementation."""

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_TENTHS, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import CLIMATES, DanthermClimateEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)

DEFAULT_TARGET_TEMPERATURE = 20.0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up climate platform."""
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Device entry not found for %s", config_entry.entry_id)
        return False

    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    if device_entry is None:
        _LOGGER.error("Device entry is None for %s", config_entry.entry_id)
        return False

    device = device_entry.get("device")
    if device is None:
        _LOGGER.error("Device object is missing in entry %s", config_entry.entry_id)
        return False

    entities = [
        DanthermClimate(device, description)
        for description in CLIMATES
        if await device.async_install_entity(description)
    ]

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermClimate(ClimateEntity, DanthermEntity, RestoreEntity):
    """Dantherm after-heater climate entity."""

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.OFF
    _attr_max_temp = 30
    _attr_min_temp = 1
    _attr_precision = PRECISION_TENTHS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermClimateEntityDescription,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._last_target_temperature = DEFAULT_TARGET_TEMPERATURE
        self._attr_current_temperature = None
        self._attr_target_temperature = self._last_target_temperature
        self._attr_hvac_action = HVACAction.OFF
        self.entity_description: DanthermClimateEntityDescription = description

    async def async_added_to_hass(self) -> None:
        """Restore the last positive target temperature."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is None:
            return

        target_temperature = last_state.attributes.get(ATTR_TEMPERATURE)
        if isinstance(target_temperature, int | float) and target_temperature > 0:
            self._last_target_temperature = float(target_temperature)
            self._attr_target_temperature = self._last_target_temperature

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        target_temperature = max(
            self.min_temp, min(float(temperature), self.max_temp)
        )
        self._last_target_temperature = target_temperature
        self._attr_target_temperature = target_temperature
        self._attr_hvac_mode = HVACMode.HEAT
        await self.coordinator.async_set_entity_state(self, target_temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the climate operating mode."""
        if hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF
            await self.coordinator.async_set_entity_state(self, 0)
            return

        if hvac_mode == HVACMode.HEAT:
            self._attr_hvac_mode = HVACMode.HEAT
            await self.coordinator.async_set_entity_state(
                self, self._last_target_temperature
            )

    def _coordinator_update(self) -> None:
        """Handle updated thermostat data from the coordinator."""
        super()._coordinator_update()

        if not self._attr_changed:
            return

        state = self._attr_new_state
        if isinstance(state, Mapping):
            current_temperature = state.get("current_temperature")
            target_temperature = state.get("target_temperature")
            heating = state.get("heating")

            if (
                not isinstance(current_temperature, int | float)
                or isinstance(current_temperature, bool)
                or not isinstance(target_temperature, int | float)
                or isinstance(target_temperature, bool)
                or not isinstance(heating, bool)
            ):
                self._attr_available = False
                self._attr_changed = True
                return

            self._attr_current_temperature = float(current_temperature)
        else:
            target_temperature = state
            heating = False

            if not isinstance(target_temperature, int | float) or isinstance(
                target_temperature, bool
            ):
                self._attr_available = False
                self._attr_changed = True
                return

        if isinstance(target_temperature, int | float):
            target_temperature = float(target_temperature)
            if target_temperature > 0:
                self._last_target_temperature = target_temperature
                self._attr_target_temperature = target_temperature
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_hvac_action = (
                    HVACAction.HEATING if heating else HVACAction.IDLE
                )
            else:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF
