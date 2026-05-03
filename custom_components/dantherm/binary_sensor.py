"""Binary sensor implementation."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import (
    ATTR_ACTIONS_PENDING,
    BINARY_SENSORS,
    DanthermBinarySensorEntityDescription,
)
from .entity import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up binary sensor platform."""
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
    for description in BINARY_SENSORS:
        if await device.async_install_entity(description):
            if description.key == ATTR_ACTIONS_PENDING:
                sensor: DanthermBinarySensor = ActionPendingBinarySensor(
                    device, description
                )
            else:
                sensor = DanthermBinarySensor(device, description)
            entities.append(sensor)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermBinarySensor(BinarySensorEntity, DanthermEntity):
    """Dantherm binary sensor."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermBinarySensorEntityDescription,
    ) -> None:
        """Init binary sensor."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_is_on = False
        self.entity_description: DanthermBinarySensorEntityDescription = description

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._coordinator_update()

        if self._attr_changed:
            self._attr_is_on = bool(self._attr_new_state)


class ActionPendingBinarySensor(DanthermBinarySensor):
    """Binary sensor that reflects whether any entity on the device has a pending action.

    Overrides ``is_on`` to read directly from the coordinator so that
    ``async_write_ha_state`` calls triggered outside the normal polling cycle
    (e.g. immediately after a write is enqueued) always return the live value.
    """

    @property
    def is_on(self) -> bool:
        """Return True when any entity on this device has a pending action."""
        return self.coordinator.has_pending_actions()

    def async_write_ha_state(self) -> None:
        """Sync _attr_is_on from live coordinator value before writing state.

        This ensures _attr_is_on is always up-to-date even when
        async_write_ha_state is called outside the normal coordinator cycle
        (e.g. by _write_pending_aware_states), so _coordinator_update can
        correctly detect the transition back to False.
        """
        self._attr_is_on = self.coordinator.has_pending_actions()
        super().async_write_ha_state()

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Skip the base class data-dict path; determine changed state directly.
        self._attr_changed = False

        if not self.coordinator.last_update_success:
            if self._attr_available:
                self._attr_changed = True
                self._attr_available = False
            return

        if not self._attr_available:
            self._attr_changed = True
            self._attr_available = True

        new_is_on = self.coordinator.has_pending_actions()
        if new_is_on != self._attr_is_on:
            self._attr_changed = True
            self._attr_is_on = new_is_on
