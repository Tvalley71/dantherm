"""Switch implementation."""

import logging

from homeassistant.components.switch import STATE_ON, SwitchEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import RESTORE_SWITCHES, SWITCHES, DanthermSwitchEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    if device_entry is None:
        _LOGGER.error("Device entry not found for %s", config_entry.entry_id)
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
    for description in RESTORE_SWITCHES:
        if await device.async_install_entity(description):
            switch = DanthermRestoreSwitch(device, description)
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

    async def _async_turn_state(self, state):
        """Turn the entity state on or off."""
        desc = self.entity_description

        self._attr_is_on = state
        self._attr_icon = desc.icon_on if state else desc.icon_off

        value = None
        if state:
            value = desc.state_seton or desc.state_on
        else:
            value = desc.state_setoff or desc.state_off

        await self.coordinator.async_set_entity_state(self, value)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._async_turn_state(False)

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._async_turn_state(True)

    def _coordinator_update(self) -> None:
        """Update data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            new_state = self._attr_new_state
            if isinstance(new_state, bool):
                self._attr_is_on = new_state
            elif (
                new_state is not None and new_state & self.entity_description.state_on
            ) == self.entity_description.state_on:
                self._attr_is_on = True
            else:
                self._attr_is_on = False

            if self._attr_is_on:
                self._attr_icon = self.entity_description.icon_on
            else:
                self._attr_icon = self.entity_description.icon_off


class DanthermRestoreSwitch(DanthermSwitch, RestoreEntity):
    """Dantherm Restore Switch Entity."""

    async def async_added_to_hass(self):
        """Register entity for refresh interval."""

        await super().async_added_to_hass()

        # Retrieve the last stored state if it exists
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            None,
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            await self.coordinator.async_restore_entity_state(
                self, last_state.state == STATE_ON
            )
