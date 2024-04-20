"""Select implementation."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from . import DanthermEntity
from .const import DOMAIN, SELECT_TYPES, DanthermSelectEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in SELECT_TYPES.values():
        if await device.async_install_entity(entity_description):
            select = DanthermSelect(device, entity_description)
            entities.append(select)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSelect(SelectEntity, DanthermEntity):
    """Dantherm select."""

    def __init__(
        self,
        device,
        description: DanthermSelectEntityDescription,
    ) -> None:
        """Init select."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermSelectEntityDescription = description

    # async def async_added_to_hass(self):
    #     """Register entity for ."""
    #     self._device.async_add_refresh_entity(self)

    # async def async_will_remove_from_hass(self) -> None:
    #     """Unregister callbacks."""
    #     self._device.async_remove_refresh_entity(self)

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

    @property
    def icon(self) -> str | None:
        """Return an icon."""
        if len(self.options) > 0:
            return self.entity_description.icon
        return "mdi:alert-circle-outline"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

        await self._device.write_holding_registers(
            description=self.entity_description, value=int(option)
        )

    async def async_update(self) -> None:
        """Fetch new state data for the select."""

        if self.entity_description.data_entity:
            result = self._device.data.get(self.entity_description.data_entity, None)
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )

        if result is None:
            self._attr_available = False
            self._attr_current_option = None
        else:
            self._attr_available = True
            if self.entity_description.data_bitwise_and:
                result &= self.entity_description.data_bitwise_and

            self._attr_current_option = str(result)
