"""Switch implementation."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import SWITCHES, DanthermSwitchEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up switch platform."""
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
    for description in SWITCHES:
        if await device.async_install_entity(description):
            switch = DanthermSwitch(device, description)
            entities.append(switch)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSwitch(SwitchEntity, DanthermEntity):
    """Dantherm switch."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermSwitchEntityDescription,
    ) -> None:
        """Init switch."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_is_on = False
        self._attr_icon = description.icon_off or description.icon
        self.entity_description: DanthermSwitchEntityDescription = description

    async def _turn_state(self, state: bool) -> None:
        """Turn the entity state on or off."""
        desc = self.entity_description

        self._attr_is_on = state
        self._attr_icon = desc.icon_on if state else desc.icon_off

        await self.coordinator.async_set_entity_state(self, state)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self._turn_state(False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self._turn_state(True)

    def _determine_switch_state(self, new_state: Any) -> bool:
        """Determine switch state from coordinator data."""
        if isinstance(new_state, bool):
            return new_state

        if new_state is None:
            return False

        # Handle numeric state with bitwise operation
        state_on = self.entity_description.state_on
        if state_on is not None and isinstance(new_state, int):
            return (new_state & state_on) == state_on

        # Default to boolean conversion
        return bool(new_state)

    def _coordinator_update(self) -> None:
        """Update data from the coordinator."""
        super()._coordinator_update()

        if self._attr_changed:
            self._attr_is_on = self._determine_switch_state(self._attr_new_state)

            # Update icon based on state
            if self._attr_is_on:
                self._attr_icon = self.entity_description.icon_on
            else:
                self._attr_icon = self.entity_description.icon_off
