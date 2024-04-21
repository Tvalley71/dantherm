"""Cover implementation."""

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from .const import COVER_TYPES, DOMAIN, DanthermCoverEntityDescription
from .device import DanthermEntity, Device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in COVER_TYPES.values():
        if await device.async_install_entity(entity_description):
            cover = DanthermCover(device, entity_description)
            entities.append(cover)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermCover(CoverEntity, DanthermEntity):
    """Dantherm cover."""

    def __init__(
        self,
        device: Device,
        description: DanthermCoverEntityDescription,
    ) -> None:
        """Init cover."""
        super().__init__(device)
        self._device = device
        self.has_entity_name = True
        self.entity_description: DanthermCoverEntityDescription = description
        self._attr_supported_features = 0
        if description.state_open:
            self._attr_supported_features |= CoverEntityFeature.OPEN
        if description.state_close:
            self._attr_supported_features |= CoverEntityFeature.CLOSE
        if description.state_stop:
            self._attr_supported_features |= CoverEntityFeature.STOP

        # states
        self._attr_is_closed = False
        self._attr_is_closing = False
        self._attr_is_opening = False
        self._attr_last_state: int = 0
        self._call_active = False

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        result = await self._device.write_holding_registers(
            description=self.entity_description,
            value=self.entity_description.state_open,
        )
        self._attr_available = result is not None
        self.async_update_ha_state(True)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        result = await self._device.write_holding_registers(
            description=self.entity_description,
            value=self.entity_description.state_close,
        )
        self._attr_available = result is not None
        self.async_update_ha_state(True)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""
        result = await self._device.write_holding_registers(
            description=self.entity_description,
            value=self.entity_description.state_stop,
        )
        self._attr_available = result is not None
        self.async_update_ha_state(True)

    @property
    def native_value(self):
        """Return the state."""
        return self._device.data.get(self.key, None)

    async def async_update(self, now: datetime | None = None) -> None:
        """Update the state of the cover."""

        self._attr_last_state = STATE_UNKNOWN
        result = await self._device.read_holding_registers(
            description=self.entity_description
        )

        if result is None:
            self._attr_available = False
        elif result == self.entity_description.state_closed:
            self._attr_state = STATE_CLOSED
            self._attr_is_closed = True
            self._attr_is_closing = False
            self._attr_is_opening = False
        elif result == self.entity_description.state_closing:
            self._attr_state = STATE_CLOSING
            self._attr_is_closing = True
        elif result == self.entity_description.state_opening:
            self._attr_state = STATE_OPENING
            self._attr_is_opening = True
        elif result == self.entity_description.state_open:
            self._attr_state = STATE_OPEN
            self._attr_is_closed = False
            self._attr_is_closing = False
            self._attr_is_opening = False
        else:
            self._attr_state = STATE_UNAVAILABLE
