"""Fan implementation."""

import logging
from typing import Any

from homeassistant.components.fan import FanEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import FANS, DanthermFanEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up fan platform."""
    # Check if entry exists in hass.data
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

    entities = []
    for description in FANS:
        if await device.async_install_entity(description):
            fan = DanthermFan(device, description)
            entities.append(fan)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermFan(FanEntity, DanthermEntity):
    """Dantherm fan entity."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermFanEntityDescription,
    ) -> None:
        """Initialize the fan."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self.entity_description: DanthermFanEntityDescription = description
        self._attr_supported_features = description.supported_features
        self._attr_speed_count = int_states_in_range(description.speed_range)
        self._attr_preset_modes = description.preset_modes
        # Initialize state
        self._attr_is_on = False
        self._attr_percentage = 0
        self._attr_preset_mode = None

    @property
    def is_on(self) -> bool | None:
        """Return true if fan is on."""
        return self._attr_is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        return self._attr_percentage

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return self._attr_speed_count

    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes."""
        return self._attr_preset_modes

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self._attr_preset_mode

    async def _async_set_fan_state(
        self, percentage: int | None = None, preset_mode: str | None = None
    ) -> None:
        """Set the fan state."""

        fan_state = {}

        # Handle percentage update
        if percentage is not None:
            self._attr_percentage = percentage
            if percentage == 0:
                self._attr_is_on = False
            else:
                self._attr_is_on = True

            # Convert percentage to fan level
            fan_state["fan_level"] = percentage_to_ranged_value(
                self.entity_description.speed_range, percentage
            )

        # Handle preset mode update
        if preset_mode in self.preset_modes:
            self._attr_preset_mode = preset_mode
            fan_state["preset_mode"] = preset_mode
        elif preset_mode is not None:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)

        await self.coordinator.async_set_entity_state(self, fan_state)
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        await self._async_set_fan_state(percentage=percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self._async_set_fan_state(preset_mode=preset_mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""

        if percentage is None:
            percentage = ranged_value_to_percentage(
                self.entity_description.speed_range,
                self.entity_description.speed_on,
            )
        await self._async_set_fan_state(percentage=percentage, preset_mode=preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self._async_set_fan_state(percentage=0)

    def _coordinator_update(self) -> None:
        """Update data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed and self._attr_new_state is not None:
            # Parse fan level from coordinator data
            fan_level = self._attr_new_state.get("fan_level", None)
            preset_mode = self._attr_new_state.get("preset_mode", None)

            if fan_level == 0:
                self._attr_is_on = False
                self._attr_percentage = 0
            elif fan_level is not None:
                self._attr_is_on = True
                # Convert fan level to percentage
                self._attr_percentage = ranged_value_to_percentage(
                    self.entity_description.speed_range, fan_level
                )
                if preset_mode in self._attr_preset_modes:
                    self._attr_preset_mode = preset_mode
