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

    async_add_entities(entities, update_before_add=False)  # True
    return True


class DanthermNumber(NumberEntity, DanthermEntity):
    """Dantherm number."""

    def __init__(
        self,
        device: Device,
        description: DanthermNumberEntityDescription,
    ) -> None:
        """Init number."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self.entity_description: DanthermNumberEntityDescription = description

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    async def async_set_native_value(self, value) -> None:
        """Update the current value."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(value)
        elif self.entity_description.data_store:
            await self._device.set_entity_state(self.key, value)
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=value
            )

    async def async_update(self) -> None:
        """Update the state of the number."""

        # Get extra state attributes
        self._attr_extra_state_attributes = await self._device.async_get_entity_attrs(
            self.entity_description
        )

        # Get the entity state
        result = await self._device.async_get_entity_state(self.entity_description)

        if result is None:
            self._attr_available = False
            self._device.data[self.key] = None
        else:
            self._attr_available = True

            precision = self.entity_description.data_precision
            if precision is not None:
                if precision >= 0:
                    result = round(result, precision)
                if precision == 0:
                    result = int(result)

        self._device.data[self.key] = result
