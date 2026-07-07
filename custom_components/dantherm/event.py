"""Event implementation."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import EVENTS, DanthermEventEntityDescription
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up event platform."""
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
    for description in EVENTS:
        if await device.async_install_entity(description):
            event = DanthermEvent(device, description)
            entities.append(event)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermEvent(EventEntity, DanthermEntity):
    """Dantherm event entity."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermEventEntityDescription,
    ) -> None:
        """Init event entity."""
        DanthermEntity.__init__(self, device, description)
        self._attr_has_entity_name = True
        self._attr_event_types = description.event_types or []
        self.entity_description: DanthermEventEntityDescription = description

    async def async_added_to_hass(self) -> None:
        """Register entity with device and restore last event."""
        await super().async_added_to_hass()
        await self.coordinator.async_add_entity(self)

    async def async_internal_added_to_hass(self) -> None:
        """Register restored event state with the device."""
        await super().async_internal_added_to_hass()
        self._device.register_event_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister entity from device."""
        self._device.unregister_event_entity(self)
        await self.coordinator.async_remove_entity(self)
        await super().async_will_remove_from_hass()

    def trigger_event(
        self, event_type: str, attributes: dict[str, Any] | None = None
    ) -> None:
        """Trigger an event and write state."""
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()

    @property
    def last_event_type(self) -> str | None:
        """Return the restored or last triggered event type."""
        return self.state_attributes.get("event_type")

    @property
    def last_event_attributes(self) -> dict[str, Any] | None:
        """Return the restored or last triggered event attributes."""
        return {
            key: value
            for key, value in self.state_attributes.items()
            if key != "event_type"
        } or None

    @property
    def last_event_signature(self) -> tuple[str | None, tuple[tuple[str, Any], ...]]:
        """Return a comparable signature for the last event state."""
        attributes = self.last_event_attributes or {}
        return self.last_event_type, tuple(sorted(attributes.items()))

    @property
    def available(self) -> bool:
        """Always keep event entities available.

        Event entities represent discrete occurrences, so they should remain
        available even while coordinator connectivity fluctuates.
        """
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Ignore coordinator state writes for event entities.

        Event entities should only update state when trigger_event is called.
        """
        return
