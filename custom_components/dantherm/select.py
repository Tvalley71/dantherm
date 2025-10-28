"""Select implementation."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import SELECTS, DanthermSelectEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up select platform."""
    # Check if entry exists in hass.data
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Device entry not found for %s", config_entry.entry_id)
        return False

    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    device = device_entry.get("device")
    if device is None:
        _LOGGER.error("Device object is missing in entry %s", config_entry.entry_id)
        return False

    entities = []
    for description in SELECTS:
        if await device.async_install_entity(description):
            select = DanthermSelect(device, description)
            entities.append(select)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSelect(SelectEntity, DanthermEntity):
    """Dantherm select."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermSelectEntityDescription,
    ) -> None:
        """Init select."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_current_option = None
        self.entity_description: DanthermSelectEntityDescription = description

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

        await self.coordinator.async_set_entity_state(self, option)

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            new_state = self._attr_new_state
            if new_state is None:
                self._attr_current_option = None
            else:
                if self.entity_description.data_bitwise_and:
                    new_state &= self.entity_description.data_bitwise_and

                self._attr_current_option = str(new_state)
