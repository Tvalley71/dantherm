"""Text implementation."""

import logging
import re

from homeassistant.components.sensor import HomeAssistantError
from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import TIMETEXTS, DanthermTimeTextEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up text platform."""
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
    for description in TIMETEXTS:
        if await device.async_install_entity(description):
            text = DanthermTimeText(device, description)
            entities.append(text)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermTimeText(TextEntity, DanthermEntity):
    """Dantherm time text."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermTimeTextEntityDescription,
    ) -> None:
        """Init time text."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_native_value = None
        self.entity_description: DanthermTimeTextEntityDescription = description

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""

        if re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", value):  # Validates HH:MM format
            if self.entity_description.data_setinternal:
                await getattr(
                    self._device,
                    f"set_{self.entity_description.data_setinternal}",
                )(value)
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_timeformat"
            )

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            self._attr_native_value = self._attr_new_state
