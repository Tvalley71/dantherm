"""Calendar implementation."""

from datetime import datetime
import logging
from typing import Any, Optional
import uuid

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

    _global_events = {}
    _global_loaded = False

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
        self._next_event: Optional[CalendarEvent] = None

    async def async_added_to_hass(self) -> None:
        """Load stored events when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if not self._global_loaded:
            self._global_loaded = True
            await self._load_events()

    @property
    def event(self):
        """Return the next upcoming event."""
        return self._next_event

    def _normalize_datetime(self, dt: datetime) -> datetime | None:
        """Ensure consistent timezone handling for datetime objects."""
        return dt.astimezone(datetime.now().astimezone().tzinfo).replace(microsecond=0)

    def _get_event(self, uid: str) -> dict:
        """Retrieve an event with its EXDATE list."""
        return self._global_events.get(uid, {"event": None, "exdates": []})

    def _set_event(self, uid: str, event_data):
        """Store an event with its EXDATE list."""
        self._global_events[uid] = event_data

    def _add_exdate(self, uid: str, exdate: datetime):
        """Add an EXDATE to the specified event, ensuring timezone consistency."""
        event_data = self._get_event(uid)
        if exdate not in event_data["exdates"]:
            event_data["exdates"].extend([self._normalize_datetime(exdate)])
            self._set_event(uid, event_data)
            _LOGGER.info("Added EXDATE %s for event: %s", exdate, uid)

    def _remove_exdate(self, uid: str, exdate: datetime):
        """Remove an EXDATE from the specified event."""
        exdate = self._normalize_datetime(exdate)
        event_data = self._get_event(uid)
        if exdate in event_data["exdates"]:
            event_data["exdates"].remove(exdate)
            self._set_event(uid, event_data)
            _LOGGER.info("Removed EXDATE %s for event: %s", exdate, uid)

    def _delete_event(self, uid: str):
        """Delete an event from the calendar."""
        del self._global_events[uid]

    async def _load_events(self):
        """Load events from storage."""
        data = await self._device.global_calendar_store.async_load()
        if data:
            for uid, event_data in data.items():
                self._global_events[uid] = {
                    "event": CalendarEvent(
                        uid=event_data["uid"],
                        summary=event_data["summary"],
                        start=datetime.fromisoformat(event_data["start"]),
                        end=datetime.fromisoformat(event_data["end"]),
                        location=event_data.get("location", ""),
                        description=event_data.get("description", ""),
                        rrule=event_data.get("rrule", ""),
                    ),
                    "exdates": [
                        datetime.fromisoformat(ex)
                        for ex in event_data.get("exdates", [])
                    ],
                }
            _LOGGER.info("Loaded %d events from storage", len(self._global_events))

    async def _save_events(self):
        """Save current events to storage."""
        data = {
            uid: {
                "uid": event["event"].uid,
                "summary": event["event"].summary,
                "start": event["event"].start.isoformat(),
                "end": event["event"].end.isoformat(),
                "location": event["event"].location,
                "description": event["event"].description,
                "rrule": event["event"].rrule,
                "exdates": [ex.isoformat() for ex in event["exdates"]],
            }
            for uid, event in self._global_events.items()
        }
        await self._device.global_calendar_store.async_save(data)
        _LOGGER.info("Saved %d events to storage", len(self._global_events))

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ):
        """Return calendar events within a datetime range."""
        events = []

        for data in self._global_events.values():
            event = data["event"]
            exdates = {self._normalize_datetime(ex) for ex in data["exdates"]}

            if event.rrule:
                rule = rrulestr(
                    event.rrule,
                    dtstart=self._normalize_datetime(event.start),
                )

                for start in rule.between(start_date, end_date, inc=True):
                    if start not in exdates:
                        events.append(  # noqa: PERF401
                            CalendarEvent(
                                uid=event.uid,
                                summary=event.summary,
                                start=start,
                                end=start
                                + (
                                    self._normalize_datetime(event.end)
                                    - self._normalize_datetime(event.start)
                                ),
                                location=event.location,
                                description=event.description,
                                rrule=event.rrule,
                                recurrence_id=start.strftime("%Y%m%dT%H%M%S"),
                            )
                        )
            elif start_date <= self._normalize_datetime(event.start) <= end_date:
                events.append(event)

        return events

    async def async_create_event(self, **kwargs: Any) -> None:
        """Add a new event to calendar."""
        if not self._evaluate_event(**kwargs):
            return False

        uid = kwargs.get(EVENT_UID, str(uuid.uuid4()))
        event = CalendarEvent(
            uid=uid,
            summary=kwargs.get(EVENT_SUMMARY, "Unnamed Event"),
            start=self._normalize_datetime(kwargs.get(EVENT_START)),
            end=self._normalize_datetime(kwargs.get(EVENT_END)),
            location=kwargs.get(EVENT_LOCATION, ""),
            description=kwargs.get(EVENT_DESCRIPTION, ""),
            rrule=kwargs.get(EVENT_RRULE, ""),
        )
        self._set_event(uid, {"event": event, "exdates": []})
        await self._save_events()  # Save changes persistently
        _LOGGER.info("Created event: %s", uid)
        return uid

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> bool:
        """Update an existing calendar event, handling recurrence instances and ranges."""
        if uid not in self._global_events:
            _LOGGER.error("Event not found: %s", uid)
            return False

        event_data = self._get_event(uid)
        current_event = event_data["event"]

        # Normalize new event data for update
        updated_event = CalendarEvent(
            uid=current_event.uid,
            summary=event.get(EVENT_SUMMARY, current_event.summary),
            start=self._normalize_datetime(event.get(EVENT_START, current_event.start)),
            end=self._normalize_datetime(event.get(EVENT_END, current_event.end)),
            location=event.get(EVENT_LOCATION, current_event.location),
            description=event.get(EVENT_DESCRIPTION, current_event.description),
            rrule=current_event.rrule,
        )

        if recurrence_id:
            recurrence_datetime = datetime.strptime(recurrence_id, "%Y%m%dT%H%M%S")

            if recurrence_range in ("THISINSTANCE", ""):
                # Add an EXDATE for the original instance and create a new single event
                self._add_exdate(uid, recurrence_datetime)

                new_uid = str(
                    uuid.uuid4()
                )  # Generate a new UID for the updated instance
                instance_event = CalendarEvent(
                    uid=new_uid,
                    summary=updated_event.summary,
                    start=self._normalize_datetime(recurrence_datetime),
                    end=self._normalize_datetime(recurrence_datetime)
                    + (updated_event.end - updated_event.start),
                    location=updated_event.location,
                    description=updated_event.description,
                )
                self._set_event(new_uid, {"event": instance_event, "exdates": []})

                _LOGGER.info(
                    "Updated specific instance %s for event: %s (new UID: %s)",
                    recurrence_id,
                    uid,
                    new_uid,
                )

            elif recurrence_range == "THISANDALLFUTURE":
                # Adjust the original event to end before the current instance
                old_rrule = rrulestr(current_event.rrule, dtstart=current_event.start)
                new_until = recurrence_datetime - (
                    current_event.end - current_event.start
                )
                new_rrule = old_rrule.replace(until=new_until)

                current_event.rrule = new_rrule.to_ical().decode("utf-8")
                self._set_event(
                    uid, {"event": current_event, "exdates": event_data["exdates"]}
                )

                # Create a new recurring event from this instance onward
                new_uid = str(uuid.uuid4())
                future_event = CalendarEvent(
                    uid=new_uid,
                    summary=updated_event.summary,
                    start=self._normalize_datetime(recurrence_datetime),
                    end=self._normalize_datetime(recurrence_datetime)
                    + (updated_event.end - updated_event.start),
                    location=updated_event.location,
                    description=updated_event.description,
                    rrule=current_event.rrule,
                )
                self._set_event(new_uid, {"event": future_event, "exdates": []})

                _LOGGER.info(
                    "Updated this and all future occurrences starting from %s for event: %s (new UID: %s)",
                    recurrence_id,
                    uid,
                    new_uid,
                )

            else:
                _LOGGER.warning("Unsupported recurrence range: %s", recurrence_range)
                return False

        else:
            # Update the entire event if no recurrence ID
            self._set_event(
                uid, {"event": updated_event, "exdates": event_data["exdates"]}
            )
            _LOGGER.info("Updated entire event: %s", uid)

        await self._save_events()  # Ensure persistence after modification
        return True

    # async def async_update_event(
    #     self,
    #     uid: str,
    #     event: dict[str, Any],
    #     recurrence_id: str | None = None,
    #     recurrence_range: str | None = None,
    # ) -> None:
    #     """Update an existing calendar event."""
    #     if uid not in self._events:
    #         _LOGGER.error("Event not found: %s", uid)
    #         return False

    #     event_data = self._get_event(uid)
    #     ev = event_data["event"]
    #     for key, value in event_data.items():
    #         if value is not None and hasattr(ev, key):
    #             setattr(ev, key, value)

    #     self._set_event(uid, event_data)
    #     await self._save_events()  # Save changes persistently
    #     _LOGGER.info("Updated event: %s", uid)
    #     return True

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> bool:
        """Delete an event on the calendar, handling recurrence instances and ranges."""

        event_data = self._get_event(uid)
        if event_data["event"] is None:
            _LOGGER.error("Event not found: %s", uid)
            return False

        event = event_data["event"]

        if recurrence_id:
            exdate = datetime.strptime(recurrence_id, "%Y%m%dT%H%M%S")
            self._add_exdate(uid, exdate)

            if recurrence_range == "THISANDALLFUTURE":
                # Adjust the RRULE to end before this recurrence.
                old_rrule = rrulestr(event.rrule, dtstart=event.start)
                new_until = (
                    exdate - event.end + event.start
                )  # Ensure recurrence ends before the current instance
                new_rrule = old_rrule.replace(until=new_until)

                # Update the event's RRULE
                event.rrule = new_rrule.to_ical().decode("utf-8")
                self._set_event(uid, {"event": event, "exdates": event_data["exdates"]})

                _LOGGER.info(
                    "Deleted instance and all future occurrences starting from %s for event: %s",
                    recurrence_id,
                    uid,
                )

            elif recurrence_range == "THISINSTANCE":
                # Only exclude the specific instance
                _LOGGER.info(
                    "Deleted specific recurrence instance %s for event: %s",
                    recurrence_id,
                    uid,
                )

            await self._save_events()  # Ensure persistence after modification
            return True

        # If no recurrence_id, delete the entire event.
        self._delete_event(uid)
        await self._save_events()  # Ensure persistence after modification
        _LOGGER.info("Deleted entire event: %s", uid)
        return True

    # async def async_delete_event(
    #     self,
    #     uid: str,
    #     recurrence_id: str | None = None,
    #     recurrence_range: str | None = None,
    # ) -> None:
    #     """Delete an event on the calendar."""

    #     event_data = self._get_event(uid)
    #     if event_data["event"] is None:
    #         _LOGGER.error("Event not found: %s", uid)
    #         return False

    #     if recurrence_id:
    #         exdate = datetime.strptime(recurrence_id, "%Y%m%dT%H%M%S")
    #         self._add_exdate(uid, exdate)
    #         await self._save_events()  # Save changes persistently
    #         return True

    #     self._delete_event(uid)
    #     await self._save_events()  # Save changes persistently
    #     _LOGGER.info("Deleted event: %s", uid)
    #     return True

    def _evaluate_event(self, **event_data):
        """Evaluate the event."""

        # Ensure summary and description contain valid event words
        summary = event_data.get(EVENT_SUMMARY, "")
        description = event_data.get(EVENT_DESCRIPTION, "")
        if not (EVENT_WORDS.get(summary, None) or EVENT_WORDS.get(description, None)):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_event_word",
            )

        # Ensure start date
        start = event_data.get(EVENT_START)
        if not start:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_event_start_time",
            )

        # Ensure end date
        end = event_data.get(EVENT_END)
        if not end:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_event_end_time",
            )

        return True
