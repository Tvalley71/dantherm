"""Number implementation."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import NUMBERS, RESTORE_NUMBERS, DanthermNumberEntityDescription
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
    for description in NUMBERS:
        if await device.async_install_entity(description):
            cover = DanthermNumber(device, description)
            entities.append(cover)
    for description in RESTORE_NUMBERS:
        if await device.async_install_entity(description):
            cover = DanthermRestoreNumber(device, description)
            entities.append(cover)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermNumber(NumberEntity, DanthermEntity):
    """Dantherm number."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermNumberEntityDescription,
    ) -> None:
        """Init number."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_native_value = None
        self.entity_description: DanthermNumberEntityDescription = description

    async def async_set_native_value(self, value) -> None:
        """Update the current value."""

        await self.coordinator.async_set_entity_state(self, value)

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            new_state = self._attr_new_state
            if new_state is None:
                self._attr_native_value = None
            else:
                precision = self.entity_description.data_precision
                if precision is not None:
                    if precision >= 0:
                        new_state = round(new_state, precision)
                    if precision == 0:
                        new_state = int(new_state)
                self._attr_native_value = new_state


class DanthermRestoreNumber(DanthermNumber, RestoreEntity):
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
            try:
                # Convert the stored state to a number if possible
                state = float(last_state.state)
            except (ValueError, TypeError):
                # Fallback to the default value in the entity description
                state = self.entity_description.data_default

            await self.coordinator.async_restore_entity_state(self, state)
