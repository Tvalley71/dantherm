"""Calendar implementation."""

from datetime import datetime
import logging
from typing import Any
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
    CalendarEvent as HA_CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.translation import async_get_translations

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
        async_add_entities([calendar], update_before_add=False)
        return True

    return False


async def get_translated_event_word(hass: HomeAssistant, word: str) -> str | None:
    """Get translated event word if found in event_words."""
    translations = await async_get_translations(
        hass, hass.config.language, "event_words", DOMAIN
    )
    return translations.get(word, None)


async def get_event_word_from_translation(
    hass: HomeAssistant, localized_word: str
) -> str | None:
    """Get event word from translation."""
    translations = await async_get_translations(
        hass, hass.config.language, "event_words", DOMAIN
    )
    for key, val in translations.items():
        # Use case-insensitive comparison if needed
        if val.lower() == localized_word.lower():
            return key
    return None


def _normalize_datetime(dt: datetime | None) -> datetime | None:
    """Ensure consistent timezone handling for datetime objects, including all-day events."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.astimezone(datetime.now().astimezone().tzinfo).replace(microsecond=0)
    # If dt is a date (no time), treat it as all-day
    return datetime.combine(dt, datetime.min.time()).astimezone(
        datetime.now().astimezone().tzinfo
    )


class DanthermCalendar(CalendarEntity, DanthermEntity):
    """Dantherm schedule calendar."""

    _global_events: dict[str, dict[str, Any]] = {}
    _global_loaded: bool = False

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
        self._next_event: CalendarEvent | None = None

    async def async_added_to_hass(self) -> None:
        """Load stored events when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if not self._global_loaded:
            self._global_loaded = True
            await self._load_events()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._next_event

    def _normalize_datetime(self, dt: datetime) -> datetime | None:
        """Ensure consistent timezone handling for datetime objects."""
        return dt.astimezone(datetime.now().astimezone().tzinfo).replace(microsecond=0)

    async def _load_events(self) -> None:
        """Load events from storage."""
        data = await self._device.global_calendar_store.async_load()
        if data:
            for uid, event_data in data.items():
                self._global_events[uid] = {
                    "event": CalendarEvent(
                        uid=event_data["uid"],
                        summary=await get_translated_event_word(
                            self.hass, event_data["summary"]
                        ),
                        start=_normalize_datetime(
                            datetime.fromisoformat(event_data["start"])
                        ),
                        end=_normalize_datetime(
                            datetime.fromisoformat(event_data["end"])
                        ),
                        location=event_data.get("location", ""),
                        description=event_data.get("description", ""),
                        rrule=event_data.get("rrule", ""),
                    ),
                    "exdates": [
                        _normalize_datetime(datetime.fromisoformat(ex))
                        for ex in event_data.get("exdates", [])
                    ],
                }
            _LOGGER.info("Loaded %d events into calendar", len(self._global_events))

    def _get_event(self, uid: str) -> dict[str, Any]:
        """Retrieve an event with its EXDATE list."""
        return self._global_events.get(uid, {"event": None, "exdates": []})

    def _set_event(self, uid: str, event_data: dict[str, Any]) -> None:
        """Store an event with its EXDATE list."""
        self._global_events[uid] = event_data

    def _add_exdate(self, uid: str, exdate: datetime) -> None:
        """Add an EXDATE to the specified event, ensuring timezone consistency."""
        event_data = self._get_event(uid)
        exdate_n = self._normalize_datetime(exdate)
        if exdate_n not in event_data["exdates"]:
            event_data["exdates"].append(exdate_n)
            self._set_event(uid, event_data)
            _LOGGER.info("Added EXDATE %s for event: %s", exdate_n, uid)

    def _remove_exdate(self, uid: str, exdate: datetime) -> None:
        """Remove an EXDATE from the specified event."""
        exdate_n = self._normalize_datetime(exdate)
        event_data = self._get_event(uid)
        if exdate_n in event_data["exdates"]:
            event_data["exdates"].remove(exdate_n)
            self._set_event(uid, event_data)
            _LOGGER.info("Removed EXDATE %s for event: %s", exdate_n, uid)

    def _delete_event(self, uid: str) -> None:
        """Delete an event from the calendar."""
        if uid in self._global_events:
            del self._global_events[uid]

    async def _save_events(self) -> None:
        """Save the current _global_events dictionary to storage."""
        out = {}
        for uid, evdata in self._global_events.items():
            c_event: CalendarEvent = evdata["event"]
            out[uid] = {
                "uid": c_event.uid,
                "summary": c_event.summary,
                "start": c_event.start.isoformat() if c_event.start else None,
                "end": c_event.end.isoformat() if c_event.end else None,
                "location": c_event.location,
                "description": c_event.description,
                "rrule": c_event.rrule,
                "exdates": [ex.isoformat() for ex in evdata["exdates"] if ex],
            }
        await self._device.global_calendar_store.async_save(out)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return all events in a filtered manner."""
        events: list[CalendarEvent] = []
        for evdict in self._global_events.values():
            event = evdict["event"]
            if not event:
                continue

            # Calculate recurrence, if any.
            # If rrule is present, we use rrulestr to expand the events.
            rrule_str = event.rrule
            exdates = {self._normalize_datetime(ex) for ex in evdict["exdates"]}

            if rrule_str:
                dtstart = self._normalize_datetime(event.start)
                until = None
                # We use the ICS standard param UNTIL if present in the rrule.
                # For now, skipping that parsing; it can be extracted from the string.
                rule = rrulestr(
                    rrule_str,
                    dtstart=dtstart,
                    forceset=True,
                )
                for occurrence in rule.between(start_date, end_date, inc=True):
                    if occurrence in exdates:
                        continue
                    occurrence_start = self._normalize_datetime(occurrence)
                    # For all-day events, if event.end is None, treat as same day.
                    if event.end:
                        occurrence_duration = self._normalize_datetime(
                            event.end
                        ) - self._normalize_datetime(event.start)
                        occurrence_end = occurrence_start + occurrence_duration
                    else:
                        occurrence_end = occurrence_start
                    if not (occurrence_end < start_date or occurrence_start > end_date):
                        c = CalendarEvent(
                            summary=get_translated_event_word(event.summary),
                            start=occurrence_start,
                            end=occurrence_end,
                            uid=event.uid,
                            location=event.location,
                            description=event.description,
                            rrule=event.rrule,
                        )
                        events.append(c)
            else:
                # Non-recurring event
                ev_start = self._normalize_datetime(event.start)
                ev_end = self._normalize_datetime(event.end)
                if ev_start is None or ev_end is None:
                    continue
                if ev_end < start_date or ev_start > end_date:
                    continue
                # Check if event is excluded by exdates
                if any(abs((ev_start - ed).total_seconds()) < 60 for ed in exdates):
                    continue

                events.append(event)

        return sorted(events, key=lambda e: (e.start or datetime.min))

    async def async_create_event(self, **kwargs: Any) -> None:
        """Create a new event."""
        if not self._evaluate_event(**kwargs):
            return False

        new_uid = str(uuid.uuid4())
        c_event = CalendarEvent(
            uid=new_uid,
            summary=kwargs.get(EVENT_SUMMARY),
            start=_normalize_datetime(kwargs.get(EVENT_START)),
            end=_normalize_datetime(kwargs.get(EVENT_END)),
            location=kwargs.get(EVENT_LOCATION, ""),
            description=kwargs.get(EVENT_DESCRIPTION, ""),
            rrule=kwargs.get(EVENT_RRULE, ""),
        )
        self._global_events[new_uid] = {
            "event": c_event,
            "exdates": [],
        }
        await self._save_events()
        _LOGGER.info("Created new event %s", new_uid)
        return c_event

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> bool:
        """Update an existing event by uid."""
        current_data = self._get_event(uid)
        current_event = current_data["event"]
        if current_event is None:
            raise HomeAssistantError(f"Event {uid} not found.")

        new_event = {
            EVENT_SUMMARY: event.get(EVENT_SUMMARY, current_event.summary),
            EVENT_DESCRIPTION: event.get(EVENT_DESCRIPTION, current_event.description),
            EVENT_LOCATION: event.get(EVENT_LOCATION, current_event.location),
            EVENT_RRULE: event.get(EVENT_RRULE, current_event.rrule),
            EVENT_START: event.get(EVENT_START),
            EVENT_END: event.get(EVENT_END),
        }
        # If rrule changed, we might want to reset exdates
        if new_event[EVENT_RRULE] != current_event.rrule:
            current_data["exdates"] = []

        new_start = _normalize_datetime(new_event.get(EVENT_START, current_event.start))
        new_end = _normalize_datetime(new_event.get(EVENT_END, current_event.end))
        updated_event = CalendarEvent(
            uid=uid,
            summary=await get_translated_event_word(
                self.hass, new_event[EVENT_SUMMARY]
            ),
            start=new_start,
            end=new_end,
            description=new_event[EVENT_DESCRIPTION],
            location=new_event[EVENT_LOCATION],
            rrule=new_event[EVENT_RRULE],
        )
        current_data["event"] = updated_event
        self._set_event(uid, current_data)
        await self._save_events()
        _LOGGER.info("Updated event %s", uid)

    async def async_delete_event(self, uid: str) -> None:
        """Delete an event by uid."""
        self._delete_event(uid)
        await self._save_events()
        _LOGGER.info("Deleted event %s", uid)

    def _evaluate_event(self, **kwargs):
        """Evaluate the event."""

        # Ensure summary and description contain valid event words
        summary = kwargs.get(EVENT_SUMMARY, "")
        if EVENT_WORDS.get(summary, None) or get_event_word_from_translation(
            self.hsas, summary
        ):
            return True
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="invalid_event_word",
        )

        # # Ensure start date
        # start = event_data.get(EVENT_START)
        # if not start:
        #     raise HomeAssistantError(
        #         translation_domain=DOMAIN,
        #         translation_key="invalid_event_start_time",
        #     )

        # # Ensure end date
        # end = event_data.get(EVENT_END)
        # if not end:
        #     raise HomeAssistantError(
        #         translation_domain=DOMAIN,
        #         translation_key="invalid_event_end_time",
        #     )
