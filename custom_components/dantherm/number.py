"""Number implementation."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import NUMBERS, DanthermNumberEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in NUMBERS:
        if await device.async_install_entity(description):
            cover = DanthermNumber(device, description)
            entities.append(cover)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermNumber(NumberEntity, DanthermEntity):
    """Dantherm number."""

    def __init__(
        self,
        device: Device,
        description: DanthermNumberEntityDescription,
    ) -> None:
        """Init number."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermNumberEntityDescription = description

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    async def async_set_native_value(self, value: int) -> None:
        """Update the current value."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(value)
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=value
            )

    async def async_update(self) -> None:
        """Update the state of the number."""

        if hasattr(self._device, f"get_{self.key}_attrs"):
            self._attr_extra_state_attributes = getattr(
                self._device, f"{self.key}_attrs"
            )

        if self.entity_description.data_getinternal:
            result = getattr(self._device, self.entity_description.data_getinternal)
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )
        self._device.data[self.key] = result
