"""Button integration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from . import DanthermEntity
from .const import BUTTON_TYPES, DOMAIN, DanthermButtonEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in BUTTON_TYPES.values():
        if await device.async_install_entity(entity_description):
            button = DanthermButton(device, entity_description)
            entities.append(button)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermButton(ButtonEntity, DanthermEntity):
    """Dantherm button."""

    def __init__(
        self,
        device,
        description: DanthermButtonEntityDescription,
    ) -> None:
        """Init button."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermButtonEntityDescription = description

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"dantherm_{self._key}"

    @property
    def _key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self._key

    async def async_press(self) -> None:
        """Handle the button press."""

        if self.entity_description.state_entity:
            value = self._device.data.get(self._key, None)
        else:
            value = self.entity_description.state

        if not value:
            await self._device.write_holding_registers(
                description=self.entity_description, value=value
            )
