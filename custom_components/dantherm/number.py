"""Number implementation."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant

from . import DanthermEntity
from .const import DOMAIN, NUMBER_TYPES, DanthermNumberEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in NUMBER_TYPES.values():
        if await device.async_install_entity(entity_description):
            cover = DanthermNumber(device, entity_description)
            entities.append(cover)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermNumber(NumberEntity, DanthermEntity):
    """Dantherm number."""

    def __init__(
        self,
        device,
        description: DanthermNumberEntityDescription,
    ) -> None:
        """Init number."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermNumberEntityDescription = description

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"dantherm_{self._key}"

    @property
    def native_value(self):
        """Return the state."""
        return self._device.data.get(self._key, None)

    @property
    def _key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self._key

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""

        await self._device.write_holding_registers(description=self.entity_description)

    async def async_update(self) -> None:
        """Read holding register."""

        result = await self._device.read_holding_registers(
            description=self.entity_description
        )
        self._device.data[self._key] = result
