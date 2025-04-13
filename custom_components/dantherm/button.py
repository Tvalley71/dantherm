"""Button integration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import BUTTONS, DanthermButtonEntityDescription

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
    for description in BUTTONS:
        if await device.async_install_entity(description):
            button = DanthermButton(device, description)
            entities.append(button)

    async_add_entities(entities, update_before_add=False)  # True
    return True


class DanthermButton(ButtonEntity, DanthermEntity):
    """Dantherm button."""

    def __init__(
        self,
        device: Device,
        description: DanthermButtonEntityDescription,
    ) -> None:
        """Init button."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self.entity_description: DanthermButtonEntityDescription = description

    async def async_press(self) -> None:
        """Handle the button press."""

        if self.entity_description.state_entity:
            value = self._device.data.get(self.key, None)
        else:
            value = self.entity_description.state

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(value)
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=value
            )
