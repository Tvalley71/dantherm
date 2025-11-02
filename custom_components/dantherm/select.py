"""Select implementation."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import SELECTS, DanthermSelectEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up select platform."""
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

    def _process_state_value(self, state: int | None) -> str | None:
        """Process raw state value and apply bitwise operations."""
        if state is None:
            return None

        # Apply bitwise AND if specified
        if self.entity_description.data_bitwise_and is not None:
            state &= self.entity_description.data_bitwise_and

        return str(state)

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._coordinator_update()

        if self._attr_changed:
            self._attr_current_option = self._process_state_value(self._attr_new_state)
