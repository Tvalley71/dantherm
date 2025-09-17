"""Adaptive management implementation."""

from collections import deque
from datetime import datetime, timedelta
import os

from homeassistant.components.calendar import CalendarEvent
from homeassistant.const import STATE_HOME, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import _LOGGER, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.dt import DEFAULT_TIME_ZONE, now as ha_now, parse_datetime

from .const import DOMAIN
from .device_map import (
    ADAPTIVE_TRIGGERS,
    ATTR_ADAPTIVE_STATE,
    ATTR_BOOST_MODE,
    ATTR_BOOST_MODE_TIMEOUT,
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_BOOST_OPERATION_SELECTION,
    ATTR_CALENDAR,
    ATTR_ECO_MODE,
    ATTR_ECO_MODE_TIMEOUT,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_ECO_OPERATION_SELECTION,
    ATTR_HOME_MODE,
    ATTR_HOME_MODE_TIMEOUT,
    ATTR_HOME_MODE_TRIGGER,
    ATTR_HOME_OPERATION_SELECTION,
    STATE_BOOST,
    STATE_ECO,
    STATE_FIREPLACE,
    STATE_NIGHT,
    STATE_PRIORITIES,
)
from .translations import async_get_adaptive_state_from_text

# This is used to determine if the debug mode is enabled.
IS_DEBUG = os.getenv("DANTHERM_DEBUG") == "1"

# This is used to represent the minimum datetime value in the system.
MIN_DATETIME = datetime.min.replace(tzinfo=DEFAULT_TIME_ZONE)

# This is used to represent the maximum datetime value in the system.
MAX_DATETIME = datetime.max.replace(tzinfo=DEFAULT_TIME_ZONE)


class DanthermAdaptiveManager:
    """Manage adaptive states and triggers for Dantherm devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init adaptive manager."""
        self._hass = hass

        # Timeout for the earliest operation change
        self._operation_change_timeout = MIN_DATETIME

        # List of active calendar events
        self._active_calendar_events: list[CalendarEvent] = []

        # Stack to manage adaptive events
        self.events = AdaptiveEventStack()

        self._adaptive_triggers = {
            ATTR_BOOST_MODE_TRIGGER: {
                "name": "boost",
                "associated_entities": [
                    ATTR_BOOST_MODE,
                    ATTR_BOOST_MODE_TIMEOUT,
                    ATTR_BOOST_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
            ATTR_ECO_MODE_TRIGGER: {
                "name": "eco",
                "associated_entities": [
                    ATTR_ECO_MODE,
                    ATTR_ECO_MODE_TIMEOUT,
                    ATTR_ECO_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
            ATTR_HOME_MODE_TRIGGER: {
                "name": "home",
                "associated_entities": [
                    ATTR_HOME_MODE,
                    ATTR_HOME_MODE_TIMEOUT,
                    ATTR_HOME_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
        }

    async def async_set_up_adaptive_triggers(self, options: dict):
        """Enable/disable associated entities based on configured adaptive triggers."""
        entities = self.get_device_entities()

        any_trigger_available = False

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)

            enabled = bool(trigger_entity)
            if enabled:
                any_trigger_available = True

            trigger_data = self._adaptive_triggers.get(trigger)
            if not trigger_data:
                _LOGGER.debug("No data for trigger: %s", trigger)
                continue

            for entity_name in trigger_data["associated_entities"]:
                self.set_entity_enabled_by_suffix(entities, entity_name, enabled)

        # The adaptive_state entity should be enabled or disabled if any triggers are available.
        self.set_entity_enabled_by_suffix(
            entities, ATTR_ADAPTIVE_STATE, any_trigger_available
        )

    async def async_set_up_tracking_for_adaptive_triggers(self, options: dict):
        """Set up tracking for adaptive triggers."""

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)
            if trigger_entity:
                trigger_data = self._adaptive_triggers[trigger]

                if trigger_entity != trigger_data["trigger"]:
                    if trigger_data["unsub"]:
                        trigger_data["unsub"]()  # remove previous listener
                    trigger_data["trigger"] = trigger_entity
                    if trigger_data["trigger"]:
                        trigger_data["unsub"] = async_track_state_change_event(
                            self._hass,
                            [trigger_data["trigger"]],
                            getattr(
                                self,
                                f"_async_{trigger_data['name']}_mode_trigger_changed",
                            ),
                        )

    async def async_initialize_adaptive_triggers(self) -> None:
        """Initialize adaptive triggers."""

        for trigger_name, mode_data in self._adaptive_triggers.items():
            # Get trigger entity and skip if not available
            trigger_entity = mode_data["trigger"]
            if not trigger_entity:
                continue

            # Get the trigger entity state
            state = self._hass.states.get(trigger_entity)
            if state is None:
                continue

            # Look up the event for this trigger
            event = self.lookup_event(mode_data["name"])
            if event is None:
                continue

            mode_data["timeout"] = event["end_time"]

            _LOGGER.debug(
                "Adaptive trigger '%s': timeout=%s",
                trigger_name,
                mode_data["timeout"],
            )

    async def _async_adaptive_trigger_changed(self, trigger: str, event):
        """Mode trigger state change callback."""

        # Skip, if old state is None or Unknown
        old_state = event.data.get("old_state")
        if old_state is None or old_state.state == STATE_UNKNOWN:
            return

        # Skip, if new state is None
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # Check if state is detected
        mode_data = self._adaptive_triggers[trigger]
        if new_state.state == STATE_ON:
            mode_data["detected"] = ha_now()
            _LOGGER.debug("%s detected!", trigger.capitalize())

        # Check if state is undetected
        elif new_state.state == STATE_OFF:
            mode_data["undetected"] = ha_now()
            _LOGGER.debug("%s undetected!", trigger.capitalize())

    async def async_update_adaptive_state(self):
        """Update adaptive state."""

        # Update adaptive triggers and calendar events
        await self._async_update_adaptive_triggers()
        await self._update_adaptive_calendar_events()

        # Process expired events
        while (event := self.expired_event()) is not None:
            # Check if operation mode change timeout has passed
            if ha_now() < self._operation_change_timeout:
                return

            # Remove event from stack
            target_operation = self.remove_event(event)
            if target_operation:
                current_operation = self.get_current_operation

                # Set the target operation if it is different from the current operation
                await self._async_set_adaptive_target_operation(
                    target_operation, current_operation
                )

    async def _async_update_adaptive_triggers(self):
        """Update adaptive triggers."""

        triggers_to_process = []
        now = ha_now()

        for trigger_name, mode_data in self._adaptive_triggers.items():
            # Skip if there is no trigger
            if not mode_data.get("trigger"):
                continue

            detected_time = mode_data["detected"]
            undetected_time = mode_data["undetected"]
            timeout_time = mode_data["timeout"]

            sort_time = MAX_DATETIME
            if detected_time:
                if undetected_time:
                    # If 'undetected' is older than 'detected',
                    # reset 'undetected'
                    if undetected_time < detected_time:
                        mode_data["undetected"] = None
                sort_time = detected_time
            elif undetected_time:
                sort_time = undetected_time
            elif timeout_time and timeout_time < now:
                sort_time = timeout_time

            triggers_to_process.append((sort_time, trigger_name))

        # Sort triggers by priority (earliest first)
        triggers_to_process.sort(key=lambda x: x[0])

        # Process all triggers in order
        for _, trigger_name in triggers_to_process:
            await self._async_update_adaptive_trigger_state(trigger_name)

    async def _async_update_adaptive_trigger_state(self, trigger_name: str):
        """Update adaptive trigger state."""

        mode_name = trigger_name.split("_", maxsplit=1)[0]
        # Check if mode is switch on
        if not self.get_entity_state_from_coordinator(f"{mode_name}_mode", False):
            return

        mode_data = self._adaptive_triggers[trigger_name]

        if mode_data["detected"]:  # Check if the trigger is detected
            # Set new trigger timeout
            mode_data["timeout"] = self._get_adaptive_trigger_timeout(mode_name)

            # Check if this is not a repeated detection
            if not self.event_exists(mode_name):
                # Check if operation mode change timeout has passed
                if ha_now() < self._operation_change_timeout:
                    return

                current_operation = self.get_current_operation

                # Get the trigger target operation from it's selection entity
                target_operation = self.get_entity_state_from_coordinator(
                    f"{mode_name}_operation_selection", None
                )

                # Push the new event to the stack
                if self.push_event(
                    mode_name,
                    current_operation,
                    target_operation,
                    end_time=mode_data["timeout"],
                ):
                    # Set the target operation if it is different from the current operation
                    await self._async_set_adaptive_target_operation(
                        target_operation, current_operation
                    )
            else:
                # Update the event with the new timeout
                self.update_event(mode_name, end_time=mode_data["timeout"])

            mode_data["detected"] = None

        elif mode_data["undetected"]:  # Check if the trigger is undetected
            # Set new trigger timeout
            mode_data["timeout"] = self._get_adaptive_trigger_timeout(mode_name)

            # Update the event with the new timeout
            self.update_event(mode_name, end_time=mode_data["timeout"])

            mode_data["undetected"] = None

        else:
            # If the trigger is still on extend the timeout
            state = self._hass.states.get(mode_data["trigger"])
            if state and state.state == STATE_ON:
                # Set new trigger timeout
                mode_data["timeout"] = self._get_adaptive_trigger_timeout(mode_name)

                # Update the event with the new timeout
                self.update_event(mode_name, end_time=mode_data["timeout"])
            else:
                mode_data["timeout"] = None

    async def _update_adaptive_calendar_events(self):
        """Get calendar events."""

        # Get domain data
        data = self._hass.data.get(DOMAIN, None)
        if not data:
            _LOGGER.debug("No data found for domain: %s", DOMAIN)
            return

        # Get calendar data
        calendar = data.get(ATTR_CALENDAR, None)
        if not calendar:
            _LOGGER.debug("No calendar events found")
            return

        events = await calendar.async_get_active_events()
        # Check for events that have ended
        for event in self._active_calendar_events:
            if event not in events:
                if calendar.event_exists(event):
                    _LOGGER.debug("Ending calendar event: %s", event)
                    await self._async_update_adaptive_calendar_state("end", event)
                else:
                    _LOGGER.debug("Deleted calendar event: %s", event)
                    await self._async_update_adaptive_calendar_state("deleted", event)
        # Check for new events
        for event in events:
            if event not in self._active_calendar_events:
                _LOGGER.debug("Starting calendar event: %s", event)
                await self._async_update_adaptive_calendar_state("start", event)

        # Update the active calendar events
        self._active_calendar_events = events

    async def _async_update_adaptive_calendar_state(
        self, action: str, event: CalendarEvent
    ) -> None:
        """Update adaptive calendar state based on action."""

        event_id = getattr(event, "uid", None)
        # Parse the event to get the target operation (use your translation/key lookup)
        operation = await async_get_adaptive_state_from_text(self._hass, event.summary)
        if not operation:
            _LOGGER.debug("No valid operation found in event %s", event)
            return
        event_end = event.end

        current_operation = self.get_current_operation

        switch_map = {
            STATE_BOOST,
            STATE_ECO,
            STATE_FIREPLACE,
            STATE_HOME,
            STATE_NIGHT,
        }

        if operation in switch_map:
            # If the event is a switch operation, update the state of the entity
            entities = self.get_device_entities()
            entity = next(
                (e for e in entities if e.entity_id.endswith(f"_{operation}_mode")),
                None,
            )
            if entity:
                state = None
                if action == "start":
                    state = True
                elif action == "end":
                    state = False

                await self.coordinator.async_set_entity_state_from_entity_id(
                    entity.entity_id, state
                )

            return

        # Check if operation mode change timeout has passed
        if ha_now() < self._operation_change_timeout:
            return

        target_operation = None

        if action == "start":
            # Push event to the event stack and set operation if the event becomes the top most event
            if self.push_event(
                operation,
                current_operation,
                operation,
                event_id=event_id,
                end_time=event_end,
            ):
                target_operation = operation

        elif action == "end":
            # Ending events will be handled when the event expires
            pass

        elif action == "deleted":
            # Pop event from the event stack and set operation if the event is the top most event
            target_operation = self.pop_event(operation, event_id=event_id)

        # Set the target operation if it is different from the current operation
        await self._async_set_adaptive_target_operation(
            target_operation, current_operation
        )

    async def _async_boost_mode_trigger_changed(self, event):
        """Boost trigger state change callback."""
        if self.get_entity_state_from_coordinator(ATTR_BOOST_MODE):
            await self._async_adaptive_trigger_changed(ATTR_BOOST_MODE_TRIGGER, event)

    async def _async_eco_mode_trigger_changed(self, event):
        """Eco trigger state change callback."""
        if self.get_entity_state_from_coordinator(ATTR_ECO_MODE):
            await self._async_adaptive_trigger_changed(ATTR_ECO_MODE_TRIGGER, event)

    async def _async_home_mode_trigger_changed(self, event):
        """Home trigger state change callback."""
        if self.get_entity_state_from_coordinator(ATTR_HOME_MODE):
            await self._async_adaptive_trigger_changed(ATTR_HOME_MODE_TRIGGER, event)

    async def _async_set_adaptive_target_operation(
        self, target_operation: str | None, current_operation: str | None
    ):
        """Set the adaptive target operation."""
        current_time = ha_now()

        # Change the operation mode if any and different from the current operation
        if not target_operation or target_operation == current_operation:
            return

        # Set the operation change timeout
        self._operation_change_timeout = current_time + (
            timedelta(seconds=30)  # Default timeout for debug mode
            if IS_DEBUG
            else timedelta(minutes=2)  # Default timeout
        )

        _LOGGER.info("Target operation = %s", target_operation)

        await self.set_operation_selection(target_operation)

    def _get_adaptive_trigger_timeout(self, mode_name: str):
        """Get adaptive trigger timeout."""
        minutes = (
            3
            if IS_DEBUG
            else self.get_entity_state_from_coordinator(f"{mode_name}_mode_timeout", 5)
        )
        return ha_now() + timedelta(minutes=minutes)

    def push_event(
        self, event_name, current_operation, new_operation, event_id=None, end_time=None
    ) -> bool:
        """Push event to event stack."""
        result = self.events.push(
            event_name,
            current_operation,
            new_operation,
            event_id=event_id,
            end_time=end_time,
        )
        _LOGGER.debug("Push events: %s", self.events)
        return result

    def update_event(self, event_name, event_id=None, end_time=None):
        """Update event in event stack."""
        result = self.events.update(event_name, event_id=event_id, end_time=end_time)
        _LOGGER.debug("Update events: %s", self.events)
        return result

    def pop_event(self, event_name, event_id=None):
        """Pop event from event stack."""
        operation = self.events.pop(event_name, event_id=event_id)
        _LOGGER.debug("Pop events: %s = %s", event_name, operation)
        return operation

    def lookup_event(self, event_name, event_id=None):
        """Lookup event in event stack."""
        event = self.events.lookup(event_name, event_id=event_id)
        _LOGGER.debug("Lookup events: %s = %s", event_name, event)
        return event

    def expired_event(self):
        """Expire event in event stack."""
        result = self.events.expired()
        _LOGGER.debug("Expired event: %s", result)
        return result

    def event_exists(self, event_name) -> bool:
        """Check if event exists."""
        return self.events.exists(event_name)

    def remove_event(self, event):
        """Remove event from event stack."""
        operation = self.events.remove(event)
        _LOGGER.debug("Remove events: %s = %s", event, operation)
        return operation


class AdaptiveEventStack(deque):
    """Event Stack with priority and previous operation tracking."""

    def push(
        self,
        event,
        current_operation,
        new_operation,
        event_id=None,
        end_time: datetime | None = None,
    ) -> bool:
        """Push an event onto the stack based on priority.

        Returns True if the event becomes the top event, otherwise False.
        """
        for item in self:
            if item["event"] == event and item.get("event_id", None) == event_id:
                # Update operation and reposition in stack
                self.remove(item)
                break

        insert_at = len(self)
        for idx, item in enumerate(self):
            if STATE_PRIORITIES.get(event, 0) >= STATE_PRIORITIES.get(item["event"], 0):
                insert_at = idx
                break
            if item["event"] == event and item.get("event_id", None) != event_id:
                insert_at = idx
                break

        if insert_at == 0:
            self.appendleft(
                self._make_item(event, current_operation, end_time, event_id)
            )
            return True

        previous_op = self[insert_at - 1]["previous"]
        self[insert_at - 1]["previous"] = new_operation
        self.insert(insert_at, self._make_item(event, previous_op, end_time, event_id))
        return False

    def update(self, event, event_id=None, end_time=None):
        """Update the end_time for an existing event to given end_time."""
        for item in self:
            if item["event"] == event and item.get("event_id") == event_id:
                item["end_time"] = end_time
                return True
        return False

    def pop(self, event, event_id=None):
        """Remove an event (and optional ID) from the stack and adjust operation if needed.

        Returns the operation of the removed event if it was the top event, otherwise None.
        """
        for idx, item in enumerate(self):
            if item["event"] == event and item.get("event_id", None) == event_id:
                removed_item = item
                self.remove(removed_item)

                if idx == 0:
                    return removed_item["previous"]

                self[idx - 1]["previous"] = removed_item["previous"]
                return None

        return None

    def exists(self, event, event_id=None):
        """Check if an event with optional ID exists in the stack."""
        return any(
            item["event"] == event and item.get("event_id", None) == event_id
            for item in self
        )

    def lookup(self, event, event_id=None):
        """Look up the operation for a given event and optional ID in the stack."""
        for item in reversed(self):
            if item["event"] == event and item.get("event_id", None) == event_id:
                return item
        return None

    def expired(self) -> dict | None:
        """Return the oldest expired event in the stack, or None if none are expired."""
        now = ha_now()
        expired_items = [
            item
            for item in self
            if item.get("end_time") is not None
            and isinstance(item["end_time"], datetime)
            and item["end_time"] < now
        ]
        if not expired_items:
            return None
        # Return the one with the earliest end_time
        return min(
            expired_items,
            key=lambda item: item["end_time"],
        )

    def remove(self, value):
        """Remove an item from the stack.

        Returns the operation of the removed event if it was the top event, otherwise None.
        """
        result = None
        if value in self:
            if self.top() == value:
                result = value.get("previous")
            super().remove(value)
        return result

    def top(self):
        """Return the top event of the stack."""
        return self[0] if self else None

    def is_top(self, event, event_id=None):
        """Check if the given event (and optional ID) is the top event in the stack."""
        return (
            bool(self)
            and self[0]["event"] == event
            and self[0].get("event_id", None) == event_id
        )

    def to_list(self):
        """Convert the event stack to a list of items."""
        result = []
        for item in self:
            d = dict(item)
            if isinstance(d.get("end_time"), datetime):
                d["end_time"] = d["end_time"].isoformat()
            result.append(d)
        return result

    @classmethod
    def from_list(cls, items):
        """Create an event stack from a list of items."""
        stack = cls()
        for item in items:
            d = dict(item)
            if "end_time" in d and isinstance(d["end_time"], str):
                dt = parse_datetime(d["end_time"])
                d["end_time"] = dt if dt is not None else None
            stack.append(d)
        return stack

    def __repr__(self):
        """Return a string representation of the event stack."""
        return f"{self.to_list()}"

    def _make_item(
        self, event, operation, end_time: datetime | None = None, event_id=None
    ):
        """Create an item for the stack."""
        item = {"event": event}
        if event_id is not None:
            item["event_id"] = event_id
        item["previous"] = operation
        item["end_time"] = end_time
        return item
