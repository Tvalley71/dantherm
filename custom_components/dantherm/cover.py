"""Cover implementation."""

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import COVERS, DanthermCoverEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up cover platform."""
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
    for description in COVERS:
        if await device.async_install_entity(description):
            cover = DanthermCover(device, description)
            entities.append(cover)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermCover(CoverEntity, DanthermEntity):
    """Dantherm cover."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermCoverEntityDescription,
    ) -> None:
        """Init cover."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_supported_features: CoverEntityFeature = CoverEntityFeature(0)
        if description.supported_features:
            self._attr_supported_features = description.supported_features
        else:
            if description.state_open:
                self._attr_supported_features |= CoverEntityFeature.OPEN
            if description.state_close:
                self._attr_supported_features |= CoverEntityFeature.CLOSE
            if description.state_stop:
                self._attr_supported_features |= CoverEntityFeature.STOP

        # states
        self._attr_available = False
        self._attr_is_closed = False
        self._attr_is_closing = False
        self._attr_is_opening = False

        self.entity_description: DanthermCoverEntityDescription = description

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        await self.coordinator.async_set_entity_state(
            self, self.entity_description.state_open
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.coordinator.async_set_entity_state(
            self, self.entity_description.state_close
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""
        await self.coordinator.async_set_entity_state(
            self, self.entity_description.state_stop
        )

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            new_state = self._attr_new_state
            if new_state == self.entity_description.state_closed:
                self._attr_is_closed = True
                self._attr_is_closing = False
                self._attr_is_opening = False
            elif new_state == self.entity_description.state_closing:
                self._attr_is_closing = True
                self._attr_is_opening = False
                self._attr_is_closed = False
            elif new_state == self.entity_description.state_opening:
                self._attr_is_opening = True
                self._attr_is_closing = False
                self._attr_is_closed = False
            elif new_state == self.entity_description.state_opened:
                self._attr_is_closed = False
                self._attr_is_closing = False
                self._attr_is_opening = False
