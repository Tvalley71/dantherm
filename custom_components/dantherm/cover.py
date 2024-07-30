"""Cover implementation."""

import logging
from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant

from .const import COVERS, DOMAIN, DanthermCoverEntityDescription
from .device import DanthermEntity, Device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

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
        device: Device,
        description: DanthermCoverEntityDescription,
    ) -> None:
        """Init cover."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermCoverEntityDescription = description
        self._attr_supported_features = 0
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

    @property
    def icon(self) -> str | None:
        """Return an icon."""

        result = super().icon
        if hasattr(self._device, f"get_{self.key}_icon"):
            result = getattr(self._device, f"get_{self.key}_icon")
        return result

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(
                CoverEntityFeature.OPEN
            )
        else:
            await self._device.write_holding_registers(
                description=self.entity_description,
                value=self.entity_description.state_open,
            )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(
                CoverEntityFeature.CLOSE
            )
        else:
            await self._device.write_holding_registers(
                description=self.entity_description,
                value=self.entity_description.state_close,
            )
        # await self.async_update_ha_state(True)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(
                CoverEntityFeature.STOP
            )
        else:
            await self._device.write_holding_registers(
                description=self.entity_description,
                value=self.entity_description.state_stop,
            )
        # await self.async_update_ha_state(True)

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    async def async_refresh_callback(self) -> None:
        """Update the state of the cover."""

        if self.entity_description.data_getinternal:
            result = getattr(self._device, self.entity_description.data_getinternal)
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )

        if result is None:
            self._attr_available = False
        else:
            self._attr_available = True

            if result == self.entity_description.state_closed:
                self._attr_state = STATE_CLOSED
                self._attr_is_closed = True
                self._attr_is_closing = False
                self._attr_is_opening = False
            elif result == self.entity_description.state_closing:
                self._attr_state = STATE_CLOSING
                self._attr_is_closing = True
                self._attr_is_opening = False
            elif result == self.entity_description.state_opening:
                self._attr_state = STATE_OPENING
                self._attr_is_opening = True
                self._attr_is_closing = False
            elif result == self.entity_description.state_opened:
                self._attr_state = STATE_OPEN
                self._attr_is_closed = False
                self._attr_is_closing = False
                self._attr_is_opening = False
