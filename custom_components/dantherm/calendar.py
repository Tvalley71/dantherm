"""Calendar implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from dateutil.rrule import rrulestr

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.dt import now as ha_now, parse_datetime, start_of_local_day

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import ATTR_CALENDAR, CALENDAR, DanthermCalendarEntityDescription
from .entity import DanthermEntity
from .exceptions import InvalidAdaptiveState
from .translations import async_get_adaptive_state_from_text

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up Dantherm calendar entity for the first main instance only."""
    # Only create the calendar entity if it does not already exist
    calendar_entity_id = f"calendar.{DOMAIN}_calendar"
    if calendar_entity_id in hass.states.async_entity_ids("calendar"):
        _LOGGER.debug("Calendar entity %s already exists", calendar_entity_id)
        return True

    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    if device_entry is None:
        _LOGGER.error("Device entry not found for %s", config_entry.entry_id)
        return False

    device = device_entry.get("device")
    if device is None:
        _LOGGER.error("Device object is missing in entry %s", config_entry.entry_id)
        return False

    entities = []
    # Only add the first calendar entity (main)
    for description in CALENDAR:
        if await device.async_install_entity(description):
            calendar = DanthermCalendar(hass, device, description)
            calendar.entity_id = calendar_entity_id  # Ensure unique entity_id
            entities.append(calendar)
            # Store reference globally for all devices
            hass.data[DOMAIN][ATTR_CALENDAR] = calendar
            break

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermCalendar(CalendarEntity, DanthermEntity):
    """Dantherm calendar entity."""

    _storage_key = f"{DOMAIN}_calendar"
    _storage_version = 1

    def __init__(
        self,
        hass: HomeAssistant,
        device: DanthermDevice,
        description: DanthermCalendarEntityDescription,
    ) -> None:
        """Init calendar."""
        super().__init__(device, description)
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_supported_features = (
            CalendarEntityFeature.CREATE_EVENT
            | CalendarEntityFeature.UPDATE_EVENT
            | CalendarEntityFeature.DELETE_EVENT
        )
        self.entity_description: DanthermCalendarEntityDescription = description
        self._events: list[DanthermCalendarEvent] = []
        self._store = Store(hass, self._storage_version, self._storage_key)

    async def async_added_to_hass(self) -> None:
        """Load events from storage when entity is added."""
        await self._load_events()
        await super().async_added_to_hass()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[DanthermCalendarEvent]:
        """Get events for the calendar from today (or start_date if in the future) to end_date."""

        # 1) Prune stored events/series before today's midnight
        today_midnight = start_of_local_day()
        modified = False

        for evt in list(self._events):
            # Remove past one-time events
            if not evt.rrule and evt.end < today_midnight:
                self._events.remove(evt)
                modified = True
                continue

            # Remove recurring series with no future instances
            if evt.rrule:
                rule = rrulestr(evt.rrule, dtstart=evt.start)
                if rule.after(today_midnight, inc=True) is None:
                    self._events.remove(evt)
                    modified = True

        if modified:
            await self._save_events()
            self.async_write_ha_state()

        # 2) Build and return all occurrences from max(start_date, today_midnight)
        window_start = max(start_date, today_midnight)
        results: list[DanthermCalendarEvent] = []

        for evt in self._events:
            if evt.rrule:
                # Expand the recurring rule
                rule = rrulestr(evt.rrule, dtstart=evt.start)
                for occ in rule.between(window_start, end_date, inc=True):
                    # EVERY occurrence gets a recurrence_id
                    results.append(  # noqa: PERF401
                        DanthermCalendarEvent(
                            uid=evt.uid,
                            summary=evt.summary,
                            start=occ,
                            end=occ + (evt.end - evt.start),
                            description=evt.description,
                            rrule=None,
                            recurrence_id=occ.isoformat(),
                        )
                    )
            # One-time event still in window
            elif evt.start < end_date and evt.end > window_start:
                results.append(evt)

        return results

    async def async_create_event(self, **kwargs: Any) -> None:
        """Create a new calendar event."""

        summary = kwargs.get("summary")
        if not summary:
            return  # Summary is required - this should not happen

        if await async_get_adaptive_state_from_text(self._hass, summary) is None:
            _LOGGER.debug("Event summary '%s' is not a valid adaptive state", summary)
            raise InvalidAdaptiveState(summary)

        event = DanthermCalendarEvent(
            uid=kwargs.get("uid", str(uuid4())),
            summary=summary,
            start=kwargs["dtstart"],
            end=kwargs["dtend"],
            description=kwargs.get("description"),
            recurrence_id=kwargs.get("recurrence_id"),
            rrule=kwargs.get("rrule"),
        )
        self._events.append(event)
        await self._save_events()
        self.async_write_ha_state()

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
        **kwargs,
    ) -> None:
        """Update an event or a single occurrence in a recurring series.

        - If `recurrence_id` is provided, only that instance is overridden.
        - If `recurrence_range == "THIS_AND_FUTURE"`, future occurrences are modified.
        - Otherwise, the master event is fully replaced.
        """
        # Locate the master event by UID
        master = next((e for e in self._events if e.uid == uid), None)
        if not master:
            _LOGGER.warning("No event found with UID %s", uid)
            return

        # Override a single occurrence
        if recurrence_id:
            # Ensure it's a datetime object
            recurrence_id = parse_datetime(recurrence_id)

            # Create an override event without recurrence
            override = DanthermCalendarEvent(
                uid=uid,
                summary=kwargs.get("summary", master.summary),
                start=recurrence_id,
                end=recurrence_id + (master.end - master.start),
                rrule=None,
                recurrence_id=recurrence_id.isoformat(),
            )
            # Add exception date to master so that instance is skipped
            master.exdate = [*list(master.exdate or []), recurrence_id]
            self._events.append(override)
            _LOGGER.info(
                "Updated single occurrence %s for series %s", recurrence_id, uid
            )

        # Modify master and future occurrences
        elif recurrence_range == "THIS_AND_FUTURE":
            # Determine the cutoff (default to master start if not given)
            cutoff = kwargs.get("start", master.start)
            # Shorten existing RRULE to end before the cutoff
            original_rrule = master.rrule
            master.rrule = original_rrule.replace(until=cutoff - timedelta(seconds=1))
            # Create a new master for future events
            new_master = DanthermCalendarEvent(
                uid=str(uuid4()),
                summary=kwargs.get("summary", master.summary),
                start=kwargs.get("start", master.start),
                end=kwargs.get("end", master.end),
                rrule=kwargs.get("rrule", master.rrule),
            )
            self._events.append(new_master)
            _LOGGER.info(
                "Changed future occurrences for series %s starting from %s",
                uid,
                new_master.start,
            )

        # Replace the entire master event
        else:
            updated = DanthermCalendarEvent(uid=uid, **event)
            idx = self._events.index(master)
            self._events[idx] = updated
            _LOGGER.info("Replaced master event %s", uid)

        await self._save_events()
        self.async_write_ha_state()

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete an event or part of a recurring series.

        - If recurrence_range == "THIS_AND_FUTURE":
            • if recurrence_id equals the first upcoming occurrence → delete whole series
            • otherwise → trim series so no events on/after recurrence_id
        - If only recurrence_id is provided:
            skip exactly that one occurrence (add EXDATE)
        - Otherwise:
            delete a one-time event
        """
        master = next((e for e in self._events if e.uid == uid), None)
        if not master:
            _LOGGER.warning("No event found with UID %s", uid)
            return

        # If recurrence_id is provided, ensure it's a datetime object
        if recurrence_id:
            recurrence_id = parse_datetime(recurrence_id)

        # Compute first upcoming occurrence from today_midnight
        today_midnight = start_of_local_day()
        first_occurrence = None
        if master.rrule:
            rule = rrulestr(master.rrule, dtstart=master.start)
            first_occurrence = rule.after(today_midnight, inc=True)

        # 1) THISANDFUTURE branch
        if recurrence_range == "THISANDFUTURE":
            # a) Deleting first upcoming occurrence → remove entire series
            if recurrence_id is not None and recurrence_id == first_occurrence:
                self._events = [e for e in self._events if e.uid != uid]
                _LOGGER.info("Deleted entire series with UID %s", uid)
            # b) Deleting later occurrence → trim RRULE
            else:
                original_rrule = master.rrule
                master.rrule = original_rrule.replace(
                    until=recurrence_id - timedelta(seconds=1)
                )
                _LOGGER.info(
                    "Trimmed series %s so no instances occur on or after %s",
                    uid,
                    recurrence_id,
                )

        # 2) Only recurrence_id → skip single occurrence
        elif recurrence_id:
            self._exdates.setdefault(uid, []).append(recurrence_id)
            _LOGGER.info(
                "Added exception date %s for series %s (skip single occurrence)",
                recurrence_id,
                uid,
            )

        # 3) No params → delete one-time event, if it's a series master, treat as deleting only this instance:
        elif master.rrule:
            cutoff = ha_now()
            master.rrule = master.rrule.replace(until=cutoff - timedelta(seconds=1))
            _LOGGER.info(
                "Trimmed series %s so no new instances occur after now (%s)",
                uid,
                cutoff,
            )
        else:
            self._events = [e for e in self._events if e.uid != uid]
            _LOGGER.info("Deleted single one-time event with UID %s", uid)

        await self._save_events()
        self.async_write_ha_state()

    async def async_get_active_events(self) -> list[CalendarEvent]:
        """Return all events (one-time and recurring) that are currently ongoing at this moment."""

        now = ha_now()
        active: list[CalendarEvent] = []

        for evt in self._events:
            duration = evt.end - evt.start

            # a) One-time event still active?
            if not evt.rrule:
                if evt.start <= now < evt.end:
                    active.append(evt)

            # b) Recurring series: find the last occurrence that may still be active
            else:
                rule = rrulestr(evt.rrule, dtstart=evt.start)
                # Find the most recent occurrence at or before now
                last_occ = rule.before(now, inc=True)
                if last_occ and last_occ + duration > now:
                    active.append(
                        DanthermCalendarEvent(
                            uid=evt.uid,
                            summary=evt.summary,
                            start=last_occ,
                            end=last_occ + duration,
                            description=evt.description,
                            rrule=None,
                            recurrence_id=last_occ.isoformat(),
                        )
                    )

        return active

    @property
    def event(self) -> DanthermCalendarEvent | None:
        """Return the next ongoing or upcoming event.

        If an event is active right now, return that.
        Otherwise return the soonest future occurrence.
        """

        now = ha_now()
        upcoming: list[DanthermCalendarEvent] = []

        # 1) Check currently active — de-prioritise future
        for evt in self._events:
            duration = evt.end - evt.start

            if not evt.rrule:
                if evt.start <= now < evt.end:
                    return evt  # ongoing one-time event
            else:
                rule = rrulestr(evt.rrule, dtstart=evt.start)
                last_occ = rule.before(now, inc=True)
                if last_occ and last_occ + duration > now:
                    # ongoing recurring
                    return DanthermCalendarEvent(
                        uid=evt.uid,
                        summary=evt.summary,
                        start=last_occ,
                        end=last_occ + duration,
                        description=evt.description,
                        rrule=None,
                        recurrence_id=last_occ.isoformat(),
                    )

        # 2) Ingen active — find all kommende og vælg første
        window_start = now
        window_end = now + timedelta(days=365)  # eller et andet reasonable horizon
        for evt in self._events:
            if not evt.rrule:
                if evt.start > now:
                    upcoming.append(evt)
            else:
                rule = rrulestr(evt.rrule, dtstart=evt.start)
                # next_occurrence er den allerførste, der ligger efter nu
                next_occ = rule.after(now, inc=False)
                if next_occ and next_occ < window_end:
                    upcoming.append(
                        DanthermCalendarEvent(
                            uid=evt.uid,
                            summary=evt.summary,
                            start=next_occ,
                            end=next_occ + (evt.end - evt.start),
                            description=evt.description,
                            rrule=None,
                            recurrence_id=next_occ.isoformat(),
                        )
                    )

        # Sorter på start-tid og returnér den tidligste
        if upcoming:
            upcoming.sort(key=lambda e: e.start)
            return upcoming[0]

        return None

    def event_exists(self, event: DanthermCalendarEvent) -> bool:
        """Check if an event exists in the calendar."""
        return any(
            e.uid == event.uid and e.start == event.start and e.end == event.end
            for e in self._events
        )

    async def _save_events(self) -> None:
        """Save events to storage."""
        data = [evt.__dict__ for evt in self._events]
        await self._store.async_save(data)

    async def _load_events(self) -> None:
        """Load events from storage and ensure correct types."""
        data = await self._store.async_load()
        self._events = []
        if data:
            for evt in data:
                # Convert start/end to datetime if needed
                start = evt.get("start")
                end = evt.get("end")
                if isinstance(start, str):
                    start = parse_datetime(start)
                if isinstance(end, str):
                    end = parse_datetime(end)
                self._events.append(
                    DanthermCalendarEvent(
                        uid=evt.get("uid"),
                        summary=evt.get("summary"),
                        start=start,
                        end=end,
                        description=evt.get("description"),
                        recurrence_id=evt.get("recurrence_id"),
                        rrule=evt.get("rrule"),
                    )
                )


class DanthermCalendarEvent(CalendarEvent):
    """CalendarEvent extended with exception dates (EXDATE)."""

    def __init__(
        self,
        *,
        uid: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        rrule: str | None = None,
        recurrence_id: str | None = None,
        exdate: list[datetime] | None = None,
    ) -> None:
        """Initialize a calendar event with exception dates."""
        super().__init__(
            uid=uid,
            summary=summary,
            start=self._normalize_datetime(start),
            end=self._normalize_datetime(end),
            description=description,
            rrule=rrule,
            recurrence_id=recurrence_id,
        )
        # List of exception dates for this series
        self.exdate: list[datetime] = self._normalize_datetime(exdate) or []

    def _normalize_datetime(self, dt: datetime | None) -> datetime | None:
        """Ensure consistent timezone handling for datetime objects, including all-day events."""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.astimezone(ha_now().astimezone().tzinfo).replace(microsecond=0)
        # If dt is a date (no time), treat it as all-day
        return datetime.combine(dt, datetime.min.time()).astimezone(
            ha_now().astimezone().tzinfo
        )

    def to_json(self) -> dict[str, any]:
        """Convert the event to a JSON-friendly dictionary."""
        data = super().__dict__.copy()
        data["exdate"] = [dt.isoformat() for dt in self.exdate]
        return data
