import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Optional
import uuid

from dateutil import tz
from dateutil.rrule import rrulestr

from homeassistant.components.calendar import (
    EVENT_DESCRIPTION,
    EVENT_END,
    EVENT_LOCATION,
    EVENT_RRULE,
    EVENT_START,
    EVENT_SUMMARY,
    EVENT_UID,
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.dt import parse_datetime

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import CALENDAR, EVENT_WORDS, DanthermCalendarEntityDescription

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

    description = CALENDAR
    if await device.async_install_entity(description):
        calendar = DanthermCalendar(device, description)

    async_add_entities([calendar], update_before_add=False)  # True
    return True


class DanthermCalendar(CalendarEntity, DanthermEntity):
    """Dantherm schedule calendar."""

    def __init__(
        self,
        device: Device,
        description: DanthermCalendarEntityDescription,
    ) -> None:
        """Init calendar."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self._attr_supported_features = (
            CalendarEntityFeature.CREATE_EVENT
            | CalendarEntityFeature.UPDATE_EVENT
            | CalendarEntityFeature.DELETE_EVENT
        )
        self.entity_description: DanthermCalendarEntityDescription = description
        self._events: dict[str, CalendarEvent] = {}
        self._next_event: Optional[CalendarEvent] = None

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._next_event

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ):
        """Retrieve events occurring within the specified date range, including recurring instances."""
        all_events = []
        for event in self._events.values():
            if event.rrule:
                rrule = rrulestr(event.rrule, dtstart=event.start_datetime_local)
                instances = [
                    CalendarEvent(
                        uid=f"{event.uid}-{start.strftime('%Y%m%dT%H%M%S')}",
                        summary=event.summary,
                        start=start,
                        end=start
                        + (event.end_datetime_local - event.start_datetime_local),
                        location=event.location,
                        description=event.description,
                        rrule=event.rrule,
                    )
                    for start in rrule.between(start_date, end_date, inc=True)
                    if f"{event.uid}-{start.strftime('%Y%m%dT%H%M%S')}"
                    not in self._recurring_exceptions
                ]
                all_events.extend(instances)
            elif start_date <= event.start_datetime_local <= end_date:
                all_events.append(event)
        return all_events

    async def async_create_event(self, event_data: dict):
        """Create a new calendar event."""
        uid = event_data.get("uid", str(uuid.uuid4()))  # Generate UID if not provided
        start = parse_datetime(event_data.get("start"))
        end = parse_datetime(event_data.get("end"))
        rrule = event_data.get("rrule")

        if not start or not end:
            _LOGGER.error("Invalid start or end time")
            return None

        self._events[uid] = CalendarEvent(
            uid=uid,
            summary=event_data.get("summary", "Unnamed Event"),
            start=start,
            end=end,
            location=event_data.get("location"),
            description=event_data.get("description"),
            rrule=rrule,
        )

        _LOGGER.info("Created event: %s", uid)
        return uid

    async def async_update_event(self, uid: str, event_data: dict):
        """Update an existing calendar event."""
        if uid not in self._events and uid not in self._recurring_exceptions:
            _LOGGER.error("Event not found: %s", uid)
            return False

        start = parse_datetime(event_data.get("start"))
        end = parse_datetime(event_data.get("end"))
        rrule = event_data.get("rrule")

        if uid in self._events:
            event = self._events[uid]
        else:
            event = self._recurring_exceptions[uid]

        self._events[uid] = CalendarEvent(
            uid=uid,
            summary=event_data.get("summary", event.summary),
            start=start if start else event.start_datetime_local,
            end=end if end else event.end_datetime_local,
            location=event_data.get("location", event.location),
            description=event_data.get("description", event.description),
            rrule=rrule if rrule else event.rrule,
        )

        _LOGGER.info("Updated event: %s", uid)
        return True

    async def async_delete_event(self, uid: str):
        """Delete an event or a specific recurrence instance."""
        if uid in self._events:
            del self._events[uid]
            _LOGGER.info("Deleted event: %s", uid)
            return True
        elif uid in self._recurring_exceptions:
            del self._recurring_exceptions[uid]
            _LOGGER.info("Deleted recurring instance: %s", uid)
            return True
        _LOGGER.error("Event not found: %s", uid)
        return False

    async def async_create_recurring_exception(
        self, uid: str, recurrence_id: str, event_data: dict
    ):
        """Create an exception for a recurring event instance."""
        if uid not in self._events:
            _LOGGER.error("Parent recurring event not found: %s", uid)
            return None

        start = parse_datetime(event_data.get("start"))
        end = parse_datetime(event_data.get("end"))

        if not start or not end:
            _LOGGER.error("Invalid start or end time for exception")
            return None

        exception_uid = f"{uid}-{recurrence_id}"
        self._recurring_exceptions[exception_uid] = CalendarEvent(
            uid=exception_uid,
            summary=event_data.get("summary", self._events[uid].summary),
            start=start,
            end=end,
            location=event_data.get("location", self._events[uid].location),
            description=event_data.get("description", self._events[uid].description),
        )

        _LOGGER.info("Created recurring exception: %s", exception_uid)
        return exception_uid

    # async def async_get_events(
    #     self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    # ):
    #     """."""
    #     all_events = []
    #     for event in self._events.values():
    #         if event.rrule:
    #             rrule = rrulestr(event.rrule, dtstart=event.start_datetime_local)
    #             instances = [
    #                 CalendarEvent(
    #                     uid=event.uid,
    #                     summary=event.summary,
    #                     start=start,
    #                     end=start
    #                     + (event.end_datetime_local - event.start_datetime_local),
    #                     location=event.location,
    #                     description=event.description,
    #                     rrule=event.rrule,
    #                 )
    #                 for start in rrule.between(start_date, end_date, inc=True)
    #             ]
    #             all_events.extend(instances)
    #         elif start_date <= event.start_datetime <= end_date:
    #             all_events.append(event)
    #     return all_events

    # async def async_create_event(self, **event_data):
    #     """."""
    #     uid = event_data.get(
    #         EVENT_UID, str(uuid.uuid4())
    #     )  # Generate UID if not provided
    #     start = event_data.get(EVENT_START)
    #     end = event_data.get(EVENT_END)
    #     rrule = event_data.get(EVENT_RRULE)

    #     if not start or not end:
    #         _LOGGER.error("Invalid start or end time")
    #         return None

    #     self._events[uid] = CalendarEvent(
    #         uid=uid,
    #         summary=event_data.get(EVENT_SUMMARY, "Unnamed Event"),
    #         start=start,
    #         end=end,
    #         location=event_data.get(EVENT_LOCATION),
    #         description=event_data.get(EVENT_DESCRIPTION),
    #         rrule=rrule,
    #     )

    #     _LOGGER.info("Created event: %s", uid)
    #     return uid

    # async def async_update_event(self, uid: str, event_data: dict):
    #     """."""
    #     if uid not in self._events:
    #         _LOGGER.error("Event not found: %s", uid)
    #         return False

    #     start = event_data.get(EVENT_START, self._events[uid].start)
    #     end = event_data.get(EVENT_END, self._events[uid].end)
    #     rrule = event_data.get("rrule", self._events[uid].rrule)

    #     self._events[uid] = CalendarEvent(
    #         uid=uid,
    #         summary=event_data.get(EVENT_SUMMARY, self._events[uid].summary),
    #         start=start,
    #         end=end,
    #         location=event_data.get(EVENT_LOCATION, self._events[uid].location),
    #         description=event_data.get(
    #             EVENT_DESCRIPTION, self._events[uid].description
    #         ),
    #         rrule=rrule,
    #     )

    #     _LOGGER.info("Updated event: %s", uid)
    #     return True

    # async def async_delete_event(self, uid: str):
    #     """."""
    #     if uid in self._events:
    #         del self._events[uid]
    #         _LOGGER.info("Deleted event: %s", uid)
    #         return True
    #     _LOGGER.error("Event not found: %s", uid)
    #     return False

    # def process_recurrence(self, uid: str, start_date: datetime, end_date: datetime):
    #     """."""
    #     if uid not in self._events:
    #         _LOGGER.error("Event not found: %s", uid)
    #         return []

    #     event = self._events[uid]
    #     if not event.rrule:
    #         return [event]

    #     rrule = rrulestr(event.rrule, dtstart=event.start_datetime)
    #     return [
    #         CalendarEvent(
    #             uid=uid,
    #             summary=event.summary,
    #             start=start,
    #             end=start + (event.end_datetime - event.start_datetime),
    #             location=event.location,
    #             description=event.description,
    #             rrule=event.rrule,
    #         )
    #         for start in rrule.between(start_date, end_date, inc=True)
    #     ]

    # # @property
    # # def event(self):
    # #     """Return the next upcoming event."""
    # #     return self._next_event

    # # async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
    # #     """Retrieve all scheduled events, including repeated ones."""
    # #     all_events = await Device.get_calendar_events()
    # #     filtered_events = []

    # #     for event in all_events:
    # #         event_start = datetime.fromisoformat(event["dtstart"])
    # #         event_end = datetime.fromisoformat(event["dtend"])

    # #         # Ensure `start_date` and `end_date` have the same timezone as event_start
    # #         if event_start.tzinfo:
    # #             start_date = start_date.replace(tzinfo=event_start.tzinfo)
    # #             end_date = end_date.replace(tzinfo=event_start.tzinfo)
    # #         else:
    # #             # If event_start is naive, make everything naive
    # #             start_date = start_date.replace(tzinfo=None)
    # #             end_date = end_date.replace(tzinfo=None)

    # #         # Handle non-recurring events
    # #         if "rrule" not in event:
    # #             if start_date <= event_start <= end_date:
    # #                 filtered_events.append(
    # #                     CalendarEvent(
    # #                         start=event_start,
    # #                         end=event_end,
    # #                         summary=event["summary"],
    # #                         description=event.get("description", ""),
    # #                         uid=event["uid"],
    # #                     )
    # #                 )
    # #             continue

    # #         # Handle repeating events
    # #         recurrence = rrulestr(event["rrule"], dtstart=event_start)
    # #         occurrences = list(recurrence.between(start_date, end_date, inc=True))

    # #         for occurrence in occurrences:
    # #             repeated_end = (
    # #                 occurrence + (event_end - event_start) if event_end else None
    # #             )

    # #             filtered_events.append(
    # #                 CalendarEvent(
    # #                     start=occurrence,
    # #                     end=repeated_end,
    # #                     summary=event["summary"],
    # #                     description=event.get("description", ""),
    # #                     uid=event["uid"],
    # #                     rrule=event["rrule"],
    # #                     recurrence_id=occurrence.isoformat(),
    # #                 )
    # #             )

    # #     return filtered_events

    # # # async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
    # # #     """Retrieve all scheduled events, including repeated ones."""
    # # #     all_events = await Device.get_calendar_events()
    # # #     filtered_events = []

    # # #     for event in all_events:
    # # #         event_start = datetime.fromisoformat(event["dtstart"])
    # # #         event_end = datetime.fromisoformat(event["dtend"])

    # # #         # Handle non-recurring events
    # # #         if "rrule" not in event:
    # # #             if start_date <= event_start <= end_date:
    # # #                 filtered_events.append(
    # # #                     CalendarEvent(
    # # #                         start=event_start,
    # # #                         end=event_end,
    # # #                         summary=event["summary"],
    # # #                         description=event.get("description", ""),
    # # #                         uid=event["uid"],
    # # #                     )
    # # #                 )
    # # #             continue

    # # #         # Handle repeating events
    # # #         recurrence = rrulestr(event["rrule"], dtstart=event_start)
    # # #         occurrences = list(recurrence.between(start_date, end_date, inc=True))

    # # #         for occurrence in occurrences:
    # # #             repeated_end = (
    # # #                 occurrence + (event_end - event_start) if event_end else None
    # # #             )

    # # #             filtered_events.append(
    # # #                 CalendarEvent(
    # # #                     start=occurrence,  # Use the correct occurrence time
    # # #                     end=repeated_end,
    # # #                     summary=event["summary"],
    # # #                     description=event.get("description", ""),
    # # #                     uid=event["uid"],
    # # #                     rrule=event["rrule"],
    # # #                     recurrence_id=occurrence.isoformat(),  # Unique identifier for this instance
    # # #                 )
    # # #             )

    # # #     return filtered_events

    # # async def async_create_event(self, **kwargs) -> None:
    # #     """Create a new calendar event."""

    # #     summary = kwargs.get("summary", "")
    # #     if EVENT_WORDS.get(summary, None):
    # #         # Ensure start and end are properly formatted
    # #         start = kwargs.get("dtstart").isoformat() if "dtstart" in kwargs else None
    # #         if not start:
    # #             raise HomeAssistantError(
    # #                 translation_domain=DOMAIN,
    # #                 translation_key="invalid_event_start_time",
    # #             )

    # #         end = kwargs.get("dtend").isoformat() if "dtend" in kwargs else None
    # #         if not end:
    # #             raise HomeAssistantError(
    # #                 translation_domain=DOMAIN,
    # #                 translation_key="invalid_event_end_time",
    # #             )

    # #         # Store full kwargs, including repeat (RRULE)
    # #         new_event = {
    # #             "uid": str(uuid.uuid4()),  # Generate a unique ID
    # #             **kwargs,
    # #         }

    # #         # Add event to the shared calendar store
    # #         await Device.add_calendar_event(new_event)

    # #     else:
    # #         raise HomeAssistantError(
    # #             translation_domain=DOMAIN, translation_key="invalid_event_word"
    # #         )

    # # async def async_update_event(
    # #     self,
    # #     uid: str,
    # #     event: dict[str, Any],
    # #     recurrence_id: str | None = None,
    # #     recurrence_range: str | None = None,
    # # ) -> None:
    # #     """Update an existing calendar event, handling recurrence when needed."""

    # #     # Load all events
    # #     all_events = await Device.get_calendar_events()

    # #     # Find the event to update
    # #     event_to_update = next((ev for ev in all_events if ev["uid"] == uid), None)

    # #     if not event_to_update:
    # #         _LOGGER.error("Event with UID %s not found for update", uid)
    # #         return

    # #     # Handle single occurrence updates for recurring events
    # #     if recurrence_id and "rrule" in event_to_update:
    # #         _LOGGER.debug(
    # #             "Updating a single occurrence for UID %s on %s", uid, recurrence_id
    # #         )

    # #         # Convert recurrence_id to datetime
    # #         recurrence_datetime = datetime.fromisoformat(recurrence_id)

    # #         # Store an exception date for this occurrence
    # #         if "exdate" not in event_to_update:
    # #             event_to_update["exdate"] = []

    # #         event_to_update["exdate"].append(recurrence_datetime.isoformat())

    # #         # Save the updated event with exceptions
    # #         await Device.update_calendar_event(
    # #             uid, {"exdate": event_to_update["exdate"]}
    # #         )
    # #         return

    # #     # Update the entire event series
    # #     _LOGGER.debug("Updating event %s with %s", uid, event)
    # #     event_to_update.update(event)

    # #     # Save the updated event
    # #     await self._device.update_calendar_event(uid, event_to_update)

    # # # async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
    # # #     """Retrieve all scheduled events, including repeated ones."""
    # # #     all_events = await Device.get_calendar_events()
    # # #     filtered_events = []

    # # #     for event in all_events:
    # # #         event_start = datetime.fromisoformat(event["dtstart"])
    # # #         event_end = datetime.fromisoformat(event["dtend"])

    # # #         # Handle non-recurring events
    # # #         if "rrule" not in event:
    # # #             if start_date <= event_start <= end_date:
    # # #                 filtered_events.append(
    # # #                     CalendarEvent(
    # # #                         start=event_start,
    # # #                         end=event_end,
    # # #                         summary=event["summary"],
    # # #                         description=event.get("description", ""),
    # # #                         uid=event["uid"],
    # # #                     )
    # # #                 )
    # # #             continue

    # # #         # Handle repeating events
    # # #         recurrence = rrulestr(event["rrule"], dtstart=event_start)
    # # #         occurrences = list(recurrence.between(start_date, end_date, inc=True))

    # # #         for occurrence in occurrences:
    # # #             repeated_end = (
    # # #                 occurrence + (event_end - event_start) if event_end else None
    # # #             )

    # # #             filtered_events.append(
    # # #                 CalendarEvent(
    # # #                     start=occurrence,  # Use the correct occurrence time
    # # #                     end=repeated_end,
    # # #                     summary=event["summary"],
    # # #                     description=event.get("description", ""),
    # # #                     uid=event["uid"],
    # # #                     rrule=event["rrule"],
    # # #                     recurrence_id=occurrence.isoformat(),  # Unique identifier for this instance
    # # #                 )
    # # #             )

    # # #     return filtered_events

    # # # async def async_create_event(self, **kwargs) -> None:
    # # #     """Create a new calendar event."""

    # # #     summary = kwargs.get("summary", "")
    # # #     if EVENT_WORDS.get(summary, None):
    # # #         # Ensure start and end are properly formatted
    # # #         start = kwargs.get("dtstart").isoformat() if "dtstart" in kwargs else None
    # # #         if not start:
    # # #             raise HomeAssistantError(
    # # #                 translation_domain=DOMAIN,
    # # #                 translation_key="invalid_event_start_time",
    # # #             )

    # # #         end = kwargs.get("dtend").isoformat() if "dtend" in kwargs else None
    # # #         if not end:
    # # #             raise HomeAssistantError(
    # # #                 translation_domain=DOMAIN,
    # # #                 translation_key="invalid_event_end_time",
    # # #             )

    # # #         # Store full kwargs, including repeat (RRULE)
    # # #         new_event = {
    # # #             "uid": str(uuid.uuid4()),  # Generate a unique ID
    # # #             **kwargs,
    # # #         }

    # # #         # Add event to the shared calendar store
    # # #         await Device.add_calendar_event(new_event)

    # # #     else:
    # # #         raise HomeAssistantError(
    # # #             translation_domain=DOMAIN, translation_key="invalid_event_word"
    # # #         )

    # # # async def async_update_event(
    # # #     self,
    # # #     uid: str,
    # # #     event: dict[str, Any],
    # # #     recurrence_id: str | None = None,
    # # #     recurrence_range: str | None = None,
    # # # ) -> None:
    # # #     """Update an existing calendar event, handling recurrence when needed."""

    # # #     # Load all events
    # # #     all_events = await Device.get_calendar_events()

    # # #     # Find the event to update
    # # #     event_to_update = next((ev for ev in all_events if ev["uid"] == uid), None)

    # # #     if not event_to_update:
    # # #         _LOGGER.error("Event with UID %s not found for update", uid)
    # # #         return

    # # #     # Handle single occurrence updates for recurring events
    # # #     if recurrence_id and "rrule" in event_to_update:
    # # #         _LOGGER.debug(
    # # #             "Updating a single occurrence for UID %s on %s", uid, recurrence_id
    # # #         )

    # # #         # Convert recurrence_id to datetime
    # # #         recurrence_datetime = datetime.fromisoformat(recurrence_id)

    # # #         # Clone event for this specific occurrence
    # # #         new_event = event_to_update.copy()
    # # #         new_event["uid"] = str(uuid.uuid4())  # Generate a new unique ID
    # # #         new_event["dtstart"] = recurrence_datetime.isoformat()

    # # #         if "dtend" in event_to_update:
    # # #             duration = datetime.fromisoformat(
    # # #                 event_to_update["dtend"]
    # # #             ) - datetime.fromisoformat(event_to_update["dtstart"])
    # # #             new_event["dtend"] = (recurrence_datetime + duration).isoformat()

    # # #         # Apply modifications
    # # #         new_event.update(event)

    # # #         # Store new modified single occurrence
    # # #         await Device.add_calendar_event(new_event)
    # # #         return

    # # #     # Update the entire event series
    # # #     _LOGGER.debug("Updating event %s with %s", uid, event)
    # # #     event_to_update.update(event)

    # # #     # Save the updated event
    # # #     await Device.update_calendar_event(uid, event_to_update)

    # # async def async_delete_event(self, uid, recurrence_id=None, recurrence_range=None):
    # #     """Delete a calendar event, handling recurrence when needed."""

    # #     # Load the current events
    # #     all_events = await Device.get_calendar_events()

    # #     # Find the event to delete
    # #     event_to_delete = next(
    # #         (event for event in all_events if event["uid"] == uid), None
    # #     )

    # #     if not event_to_delete:
    # #         _LOGGER.error("Event with UID %s not found", uid)
    # #         return

    # #     # Handle recurring events
    # #     if recurrence_id and "rrule" in event_to_delete:
    # #         _LOGGER.debug(
    # #             "Deleting a single occurrence for %s on %s", uid, recurrence_id
    # #         )

    # #         # Convert recurrence_id to datetime for comparison
    # #         recurrence_datetime = datetime.fromisoformat(recurrence_id)

    # #         # Modify the RRULE to exclude the specific recurrence
    # #         recurrence = rrulestr(
    # #             event_to_delete["rrule"],
    # #             dtstart=datetime.fromisoformat(event_to_delete["dtstart"]),
    # #         )
    # #         modified_rule = recurrence.replace(
    # #             until=recurrence_datetime
    # #             - timedelta(seconds=1)  # Stop recurrence before the deleted event
    # #         )

    # #         event_to_delete["rrule"] = str(modified_rule)

    # #         # Save the modified event list back to storage (Fix applied here)
    # #         await Device.update_calendar_event(uid, {"rrule": event_to_delete["rrule"]})
    # #         return

    # #     # If it's a full event deletion (not a recurrence), remove it completely
    # #     await Device.delete_calendar_event(uid)

    # # async def async_update(self):
    # #     """Fetch events and check for active ones."""
    # #     now = datetime.now()
    # #     active_event = None

    # #     # for event in self._events:
    # #     #     start = event["start"]
    # #     #     end = event["end"]

    # #     #     if start <= now <= end:
    # #     #         active_event = event
    # #     #         break

    # #     # self._next_event = active_event

    # #     # if active_event:
    # #     #     event_word = active_event["summary"].strip().lower()
    # #     #     _LOGGER.debug("Active calendar event summary: %s", event_word)
    # #     #     await self._device.set_calendar_event(event_word)
