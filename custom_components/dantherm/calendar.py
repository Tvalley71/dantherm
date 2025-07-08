"""Calendar implementation."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import CALENDAR, DanthermCalendarEntityDescription
from .entity import DanthermEntity

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
    for description in CALENDAR:
        if await device.async_install_entity(description):
            calendar = DanthermCalendar(device, description)
            entities.append(calendar)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermCalendar(CalendarEntity, DanthermEntity):
    """Dantherm calendar entity."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermCalendarEntityDescription,
    ) -> None:
        """Init calendar."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self.entity_description: DanthermCalendarEntityDescription = description
        self._events: list[CalendarEvent] = []

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next event."""
        now = dt_util.now()
        for event in self._events:
            if event.start <= now <= event.end:
                return event
            if event.start > now:
                return event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get events for the calendar."""
        return [
            event
            for event in self._events
            if event.start < end_date and event.end > start_date
        ]

    async def async_create_event(self, **kwargs: Any) -> None:
        """Create a new calendar event."""
        event = CalendarEvent(
            summary=kwargs["summary"],
            start=kwargs["start"],
            end=kwargs["end"],
            description=kwargs.get("description"),
        )
        self._events.append(event)
        self.async_write_ha_state()

        # Apply the scheduled action
        await self._apply_event_action(event)

    async def _apply_event_action(self, event: CalendarEvent) -> None:
        """Apply actions based on event description."""
        if not event.description:
            return

        # Parse event description for actions
        actions = self._parse_event_actions(event.description)

        for action in actions:
            await self._execute_action(action)

    def _parse_event_actions(self, description: str) -> list[dict[str, Any]]:
        """Parse event description for automation actions."""
        actions = []

        # Example format: "operation:boost,fan_level:4,eco_mode:on"
        for action_str in description.split(","):
            if ":" not in action_str:
                continue

            key, value = action_str.strip().split(":", 1)
            actions.append({"key": key, "value": value})

        return actions

    async def _execute_action(self, action: dict[str, Any]) -> None:
        """Execute a single action."""
        key = action["key"]
        value = action["value"]

        try:
            if key == "operation":
                await self._device.async_set_operation_selection(value)
            elif key == "fan_level":
                await self._device.async_set_fan_level_selection(value)
            elif key == "boost_mode":
                await self._device.async_set_boost_mode(value.lower() == "on")
            elif key == "eco_mode":
                await self._device.async_set_eco_mode(value.lower() == "on")
            elif key == "home_mode":
                await self._device.async_set_home_mode(value.lower() == "on")
            elif key == "away_mode":
                await self._device.async_set_away_mode(value.lower() == "on")
            elif key == "night_mode":
                await self._device.async_set_night_mode(value.lower() == "on")
        except Exception as err:
            _LOGGER.error("Failed to execute action %s: %s", action, err)
