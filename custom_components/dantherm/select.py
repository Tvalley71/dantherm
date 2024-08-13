"""Select implementation."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SELECTS, DanthermSelectEntityDescription
from .device import DanthermEntity, Device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

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
        device: Device,
        description: DanthermSelectEntityDescription,
    ) -> None:
        """Init select."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermSelectEntityDescription = description

    @property
    def icon(self) -> str | None:
        """Return an icon."""

        result = super().icon
        if hasattr(self._device, f"get_{self.key}_icon"):
            result = getattr(self._device, f"get_{self.key}_icon")
        return result

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(
                option
            )
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=int(option)
            )

    async def async_update(self) -> None:
        """Update state of the select."""

        if self.entity_description.data_getinternal:
            result = getattr(self._device, self.entity_description.data_getinternal)
        elif self.entity_description.data_entity:
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
