"""Text implementation."""

import logging
import re

from homeassistant.components.sensor import HomeAssistantError
from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import TIMETEXTS, DanthermTimeTextEntityDescription

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
    for description in TIMETEXTS:
        if await device.async_install_entity(description):
            text = DanthermTimeText(device, description)
            entities.append(text)

    async_add_entities(entities, update_before_add=False)  # True
    return True


class DanthermTimeText(TextEntity, DanthermEntity):
    """Dantherm time text."""

    def __init__(
        self,
        device: Device,
        description: DanthermTimeTextEntityDescription,
    ) -> None:
        """Init time text."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermTimeTextEntityDescription = description

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    async def async_update(self) -> None:
        """Update the state of the sensor."""

        # Get the entity state
        result = await self._device.async_get_entity_state(self.entity_description)

        if result is None:
            self._attr_available = False
        else:
            self._attr_available = True
        self._device.data[self.key] = result

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""

        if re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", value):  # Validates HH:MM format
            if self.entity_description.data_setinternal:
                await getattr(self._device, self.entity_description.data_setinternal)(
                    value
                )
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_timeformat"
            )
