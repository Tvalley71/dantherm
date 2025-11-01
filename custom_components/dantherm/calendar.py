"""Calendar implementation."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from dateutil.rrule import rrulestr

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.util.dt import now as ha_now, parse_datetime, start_of_local_day

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import (
    ATTR_CALENDAR,
    CALENDAR,
    CONF_LINK_TO_PRIMARY_CALENDAR,
    DanthermCalendarEntityDescription,
)
from .entity import DanthermEntity
from .exceptions import InvalidAdaptiveState
from .helpers import (
    as_dt,
    duration_dt,
    is_primary_entry,
    parse_dt_or_date,
    rrule_trim_until,
)
from .translations import (
    async_get_adaptive_state_from_summary,
    async_get_available_adaptive_states,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dantherm calendar entities."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    # Non-primary entries may create a local calendar unless they opt out
    if not is_primary_entry(hass, config_entry.entry_id):
        link_to_primary = config_entry.options.get(CONF_LINK_TO_PRIMARY_CALENDAR, True)
        if link_to_primary:
            _LOGGER.debug(
                "Entry %s links to primary calendar; skipping local calendar",
                config_entry.entry_id,
            )
            return

    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    if device_entry is None:
        _LOGGER.error("Device entry is None for %s", config_entry.entry_id)
        return

    device: DanthermDevice | None = device_entry.get("device")
    if device is None:
        _LOGGER.error("Device object is missing in entry %s", config_entry.entry_id)
        return

    description = CALENDAR
    if await device.async_install_entity(description):
        # Per-instans storage nøgle
        storage_key = f"{DOMAIN}_calendar_{config_entry.entry_id}"
        calendar = DanthermCalendar(hass, device, description, storage_key=storage_key)
        # Set unique_id: shared for primary, per-entry for local calendars
        if is_primary_entry(hass, config_entry.entry_id):
            domain_data[ATTR_CALENDAR] = calendar
        domain_data[config_entry.entry_id][ATTR_CALENDAR] = calendar
        async_add_entities([calendar], update_before_add=True)


class DanthermCalendar(DanthermEntity, CalendarEntity):
    """Dantherm calendar entity."""

    _storage_version = 1

    def __init__(
        self,
        hass: HomeAssistant,
        device: DanthermDevice,
        description: DanthermCalendarEntityDescription,
        *,
        storage_key: str,
    ) -> None:
        """Init calendar."""
        DanthermEntity.__init__(self, device, description)
        CalendarEntity.__init__(self)
        self._hass = hass
        self._attr_has_entity_name = True
        # self._attr_unique_id = f"{DOMAIN}"
        self._attr_supported_features = (
            CalendarEntityFeature.CREATE_EVENT
            | CalendarEntityFeature.UPDATE_EVENT
            | CalendarEntityFeature.DELETE_EVENT
        )
        self.entity_description = description
        self._events: list[DanthermCalendarEvent] = []
        self._store = Store(hass, self._storage_version, storage_key)

    async def async_added_to_hass(self) -> None:
        """Load events from storage when entity is added."""
        await self._load_events()
        await super().async_added_to_hass()

        # Register with adaptive manager for event validation
        if hasattr(self._device, "events") and self._device.events:
            self._device.events.set_calendar(self)

    def _find_override(self, uid: str, occ: datetime) -> DanthermCalendarEvent | None:
        """Return override matching UID + RECURRENCE-ID for a specific occurrence."""
        occ_norm = occ.replace(microsecond=0)
        for e in self._events:
            if e.uid != uid or e.rrule or not getattr(e, "recurrence_id", None):
                continue
            rid = parse_datetime(e.recurrence_id)
            if rid and rid.replace(microsecond=0) == occ_norm:
                return e
        return None

    async def _prune_events(self) -> None:
        """Prune expired one-time events and exhausted recurring series."""
        today_midnight = start_of_local_day()
        modified = False

        for evt in list(self._events):
            # Remove past one-time events
            if not evt.rrule and as_dt(evt.end) < today_midnight:
                self._events.remove(evt)
                modified = True
                continue

            # Remove recurring series with no future instances
            if evt.rrule:
                rule = rrulestr(evt.rrule, dtstart=as_dt(evt.start))
                if rule.after(today_midnight, inc=True) is None:
                    self._events.remove(evt)
                    modified = True

        if modified:
            await self._save_events()
            self.async_write_ha_state()

    async def _expand_events_window(
        self, start_date: datetime, end_date: datetime
    ) -> list[DanthermCalendarEvent]:
        """Expand events into instances within [start_date, end_date)."""
        # Respect the requested window (do not clamp to today)
        window_start = start_date
        results: list[DanthermCalendarEvent] = []

        for evt in self._events:
            if evt.rrule:
                rule = rrulestr(evt.rrule, dtstart=as_dt(evt.start))
                exdates = {d.replace(microsecond=0) for d in (evt.exdate or [])}
                dur = duration_dt(evt.start, evt.end)

                for occ in rule.between(window_start, end_date, inc=True):
                    occ_norm = occ.replace(microsecond=0)
                    if occ_norm in exdates:
                        continue

                    if (ovr := self._find_override(evt.uid, occ_norm)) is not None:
                        results.append(ovr)
                        continue

                    results.append(
                        DanthermCalendarEvent(
                            uid=evt.uid,
                            summary=evt.summary,
                            start=occ,
                            end=occ + dur,
                            description=evt.description,
                            rrule=None,
                            recurrence_id=occ_norm.isoformat(),
                        )
                    )
            else:
                evt_start_dt = as_dt(evt.start)
                evt_end_dt = as_dt(evt.end)
                if evt_start_dt < end_date and evt_end_dt > window_start:
                    results.append(evt)

        return results

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[DanthermCalendarEvent]:
        """Get events in window and prune storage first.

        Clamp start to today so past events are not returned.
        """

        # Prune expired events before expanding
        await self._prune_events()

        # Do not return events before today
        window_start = max(as_dt(start_date), start_of_local_day())
        if as_dt(end_date) <= window_start:
            return []

        events = await self._expand_events_window(window_start, end_date)

        # De-duplicate instances which may be produced from both a series
        # (when an override is found) and the stored override entity itself.
        # Keep the first seen and drop subsequent duplicates.
        seen: set[tuple[str, str]] = set()
        unique: list[DanthermCalendarEvent] = []
        for evt in events:
            # Prefer using recurrence_id for instances; fall back to start/end
            rid = (
                evt.recurrence_id
                or f"{as_dt(evt.start).isoformat()}_{as_dt(evt.end).isoformat()}"
            )
            key = (evt.uid, rid)
            if key in seen:
                continue
            seen.add(key)
            unique.append(evt)

        # Always return in chronological order for deterministic consumers/tests
        unique.sort(key=lambda e: as_dt(e.start))
        return unique

    async def async_create_event(self, **kwargs: Any) -> None:
        """Create a new calendar event.

        Validates summary and time range before storing.
        """
        summary = kwargs.get("summary")
        if not summary:
            _LOGGER.warning("Missing summary for new calendar event")
            return

        # Validate adaptive state inside the summary (domain-specific rule)
        if await async_get_adaptive_state_from_summary(self._hass, summary) is None:
            _LOGGER.debug("Event summary '%s' is not a valid adaptive state", summary)
            # Get available states for the error message
            available_states = await async_get_available_adaptive_states(self._hass)
            # Convert to list of translated names for display
            state_names = list(available_states.values())
            raise InvalidAdaptiveState(summary, state_names)

        # Basic time sanity check
        start = kwargs["dtstart"]
        end = kwargs["dtend"]
        if as_dt(end) <= as_dt(start):
            _LOGGER.warning("End must be after start when creating event")
            return

        event = DanthermCalendarEvent(
            uid=kwargs.get("uid", str(uuid4())),
            summary=summary,
            start=start,
            end=end,
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

        - recurrence_id → override a single instance (keeps series UID + adds EXDATE)
        - recurrence_range == "THISANDFUTURE" → split series at cutoff
        - otherwise → replace the master event as-is
        """
        master = next((e for e in self._events if e.uid == uid), None)
        if not master:
            _LOGGER.warning("No event found with UID %s", uid)
            return

        # Validate adaptive state if summary is being updated
        summary = event.get("summary")
        if summary is not None:
            if await async_get_adaptive_state_from_summary(self._hass, summary) is None:
                _LOGGER.debug(
                    "Event summary '%s' is not a valid adaptive state", summary
                )
                # Get available states for the error message
                available_states = await async_get_available_adaptive_states(self._hass)
                # Convert to list of translated names for display
                state_names = list(available_states.values())
                # The exception itself will handle formatting with conjunction
                raise InvalidAdaptiveState(summary, state_names)

        # Parse recurrence_id once for reuse
        rid_dt: datetime | None = None
        if recurrence_id:
            rid_dt = parse_datetime(recurrence_id)
            if rid_dt is None:
                _LOGGER.warning(
                    "Invalid recurrence_id %s for UID %s", recurrence_id, uid
                )
                return

        # 1) Handle THISANDFUTURE first (UI sends both recurrence_id + recurrence_range)
        if recurrence_range == "THISANDFUTURE":
            if not master.rrule:
                _LOGGER.warning(
                    "Cannot apply THISANDFUTURE on non-recurring UID %s", uid
                )
                return

            # Determine cutoff (prefer explicit dtstart, then recurrence_id, then master.start)
            cutoff = (
                event.get("dtstart") or kwargs.get("start") or rid_dt or master.start
            )
            if isinstance(cutoff, str):
                cutoff = parse_datetime(cutoff)
            if cutoff is None:
                _LOGGER.warning("Missing valid cutoff for THISANDFUTURE on UID %s", uid)
                return

            original_rrule = master.rrule
            until = as_dt(cutoff) - timedelta(seconds=1)

            # Trim existing series (remove COUNT, set UNTIL)
            master.rrule = rrule_trim_until(original_rrule, until)

            # Create new master for future occurrences, preserving duration unless overridden
            duration = duration_dt(master.start, master.end)
            new_start = cutoff
            new_end = event.get("dtend") or (as_dt(new_start) + duration)
            if isinstance(new_end, str):
                new_end = parse_datetime(new_end)

            # Adjust COUNT in the new series to only include the remaining
            # number of occurrences from the cutoff (inclusive), if the
            # original rule used COUNT.
            new_rrule = event.get("rrule", original_rrule)
            if "COUNT=" in (original_rrule or ""):
                try:
                    # Compute how many occurrences happened strictly before cutoff
                    rule = rrulestr(original_rrule, dtstart=as_dt(master.start))
                    # Count occurrences strictly before cutoff, including the
                    # very first one at dtstart
                    occurred_before = len(
                        rule.between(
                            as_dt(master.start) - timedelta(seconds=1),
                            as_dt(cutoff),
                            inc=False,
                        )
                    )
                    # Extract original count
                    count_part = next(
                        (
                            p
                            for p in original_rrule.split(";")
                            if p.startswith("COUNT=")
                        ),
                        None,
                    )
                    remaining = None
                    if count_part is not None:
                        total = int(count_part.split("=", 1)[1])
                        remaining = max(total - occurred_before, 0)
                    if remaining is not None:
                        # Replace COUNT value with remaining
                        parts = []
                        for p in new_rrule.split(";"):
                            if p.startswith("COUNT="):
                                parts.append(f"COUNT={remaining}")
                            else:
                                parts.append(p)
                        new_rrule = ";".join(parts)
                except Exception:  # noqa: BLE001
                    # If anything goes wrong, keep the original rule
                    new_rrule = event.get("rrule", original_rrule)

            # Only create the new master if there are remaining occurrences
            # (when COUNT would be 0, the split results in no future items)
            create_new = True
            try:
                if "COUNT=" in (new_rrule or ""):
                    count_val = int(
                        next(
                            (p for p in new_rrule.split(";") if p.startswith("COUNT=")),
                            "COUNT=0",
                        ).split("=", 1)[1]
                    )
                    create_new = count_val > 0
            except Exception:  # noqa: BLE001
                create_new = True

            if create_new:
                new_master = DanthermCalendarEvent(
                    uid=str(uuid4()),
                    summary=event.get("summary", master.summary),
                    description=event.get("description", master.description),
                    start=new_start,
                    end=new_end,
                    rrule=new_rrule,
                )
                self._events.append(new_master)
            _LOGGER.info(
                "THISANDFUTURE applied for %s; old series until %s, new from %s",
                uid,
                until,
                new_start,
            )

        # 2) Single-occurrence override
        elif rid_dt:
            # Preserve original duration if no new end provided
            duration = duration_dt(master.start, master.end)

            new_start = event.get("dtstart", rid_dt)
            if isinstance(new_start, str):
                new_start = parse_datetime(new_start)
            new_end = event.get(
                "dtend",
                as_dt(new_start) + duration if new_start else as_dt(rid_dt) + duration,
            )
            if isinstance(new_end, str):
                new_end = parse_datetime(new_end)

            if as_dt(new_end) <= as_dt(new_start):
                _LOGGER.warning("End must be after start when overriding %s", uid)
                return

            override = DanthermCalendarEvent(
                uid=uid,  # keep series UID per RFC 5545
                summary=event.get("summary", master.summary),
                description=event.get("description", master.description),
                start=new_start,
                end=new_end,
                rrule=None,
                recurrence_id=as_dt(rid_dt).isoformat(),  # reference original instance
            )

            # Ensure EXDATE contains the original instance once (skip original)
            exdates = {d.replace(microsecond=0) for d in (master.exdate or [])}
            exdates.add(as_dt(rid_dt))
            master.exdate = sorted(exdates)

            # Replace any existing override with same UID + RECURRENCE-ID
            self._events = [
                e
                for e in self._events
                if not (
                    e.uid == uid
                    and getattr(e, "recurrence_id", None) == override.recurrence_id
                )
            ]
            self._events.append(override)
            _LOGGER.info("Updated single occurrence %s for series %s", rid_dt, uid)

        # 3) Replace entire master
        else:
            rep_start = event.get("start") or event.get("dtstart") or master.start
            rep_end = event.get("end") or event.get("dtend") or master.end
            if as_dt(rep_end) <= as_dt(rep_start):
                _LOGGER.warning("End must be after start when replacing master %s", uid)
                return

            updated = DanthermCalendarEvent(
                uid=uid,
                summary=event.get("summary", master.summary),
                description=event.get("description", master.description),
                start=rep_start,
                end=rep_end,
                rrule=event.get("rrule", master.rrule),
                exdate=event.get("exdate", master.exdate),
            )
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
        """Delete an event or part of a recurring series."""
        master = next((e for e in self._events if e.uid == uid and e.rrule), None)

        rid_dt: datetime | None = None
        if recurrence_id:
            rid_dt = parse_datetime(recurrence_id)
            if rid_dt is None:
                _LOGGER.warning(
                    "Invalid recurrence_id %s for UID %s", recurrence_id, uid
                )
                return
            rid_dt = rid_dt.replace(microsecond=0)

        # THISANDFUTURE handling (unchanged logic aside from master selection)
        if recurrence_range == "THISANDFUTURE":
            if not master or not master.rrule:
                self._events = [e for e in self._events if e.uid != uid]
                _LOGGER.info("Deleted single event(s) with UID %s", uid)
            elif rid_dt is not None:
                # Determine the true first occurrence of the series
                rule = rrulestr(master.rrule, dtstart=as_dt(master.start))
                first_occurrence = rule.after(
                    as_dt(master.start) - timedelta(seconds=1), inc=True
                )
                if first_occurrence:
                    first_occurrence = first_occurrence.replace(microsecond=0)

                if first_occurrence and rid_dt == first_occurrence:
                    self._events = [e for e in self._events if e.uid != uid]
                    _LOGGER.info("Deleted entire series with UID %s", uid)
                else:
                    until = rid_dt - timedelta(seconds=1)
                    master.rrule = rrule_trim_until(master.rrule, until)
                    self._events = [
                        e
                        for e in self._events
                        if not (
                            e.uid == uid
                            and getattr(e, "recurrence_id", None)
                            and parse_datetime(e.recurrence_id).replace(microsecond=0)
                            >= rid_dt
                        )
                    ]
                    _LOGGER.info(
                        "Trimmed series %s so no instances occur on or after %s and removed future overrides",
                        uid,
                        rid_dt,
                    )
            else:
                _LOGGER.warning(
                    "A recurrence_id is required for THISANDFUTURE on UID %s", uid
                )

        elif rid_dt is not None:
            # Delete a single occurrence
            # 1) Remove any override instance matching UID+RECURRENCE-ID
            before = len(self._events)
            self._events = [
                e
                for e in self._events
                if not (
                    e.uid == uid
                    and getattr(e, "recurrence_id", None)
                    and parse_datetime(e.recurrence_id).replace(microsecond=0) == rid_dt
                )
            ]
            removed = before - len(self._events)

            # 2) Ensure the original occurrence is skipped by EXDATE on master (if series exists)
            if master and master.rrule:
                exdates = {d.replace(microsecond=0) for d in (master.exdate or [])}
                exdates.add(rid_dt)
                master.exdate = sorted(exdates)
                _LOGGER.info(
                    "Deleted override (%s removed) and added EXDATE %s for series %s",
                    removed,
                    rid_dt,
                    uid,
                )
            else:
                # No master series: just removed the standalone override
                _LOGGER.info(
                    "Deleted standalone override for UID %s at %s", uid, rid_dt
                )

        elif master and master.rrule:
            # No parameters → delete one-time event; if series, trim at now
            cutoff = ha_now().replace(microsecond=0)
            master.rrule = rrule_trim_until(master.rrule, cutoff - timedelta(seconds=1))
            # Also remove overrides at or after now
            self._events = [
                e
                for e in self._events
                if not (
                    e.uid == uid
                    and getattr(e, "recurrence_id", None)
                    and parse_datetime(e.recurrence_id).replace(microsecond=0) >= cutoff
                )
            ]
            _LOGGER.info(
                "Trimmed series %s so no new instances occur after now (%s) and removed future overrides",
                uid,
                cutoff,
            )
        else:
            self._events = [e for e in self._events if e.uid != uid]
            _LOGGER.info("Deleted single one-time event with UID %s", uid)

        await self._save_events()
        self.async_write_ha_state()

    async def async_get_active_events(self) -> list[CalendarEvent]:
        """Return currently active events without pruning (read-only path)."""
        now = ha_now()
        active: list[CalendarEvent] = []

        for evt in self._events:
            # Handle single (non-recurring) events
            if not evt.rrule:
                start_dt = as_dt(evt.start)
                end_dt = as_dt(evt.end)
                if start_dt <= now < end_dt:
                    active.append(evt)
                continue

            # Handle recurring events
            rule = rrulestr(evt.rrule, dtstart=as_dt(evt.start))
            exdates = {as_dt(d).replace(microsecond=0) for d in (evt.exdate or [])}

            # Find the most recent occurrence at or before now
            last_occ = rule.before(now, inc=True)
            if last_occ is None:
                continue

            occ_norm = last_occ.replace(microsecond=0)

            # Skip if this occurrence is excluded
            if occ_norm in exdates:
                continue

            # Check if there's an override for this occurrence
            ovr = self._find_override(evt.uid, occ_norm)

            if ovr:
                # Use override event details
                start_dt = as_dt(ovr.start)
                end_dt = as_dt(ovr.end)
                if start_dt <= now < end_dt:
                    active.append(ovr)
            else:
                # Use original event with calculated occurrence time
                duration = duration_dt(evt.start, evt.end)
                is_all_day = isinstance(evt.start, date) and not isinstance(
                    evt.start, datetime
                )

                if is_all_day:
                    # For all-day events, convert occurrence to local day boundaries
                    start_day = last_occ.astimezone(UTC).date()
                    days = max(1, int(duration.total_seconds() // 86400))
                    start_dt = start_of_local_day(start_day)
                    end_dt = start_of_local_day(start_day + timedelta(days=days))
                else:
                    start_dt = last_occ
                    end_dt = last_occ + duration

                if start_dt <= now < end_dt:
                    # Create instance event for this occurrence
                    instance = DanthermCalendarEvent(
                        uid=evt.uid,
                        summary=evt.summary,
                        start=start_dt,
                        end=end_dt,
                        description=evt.description,
                        rrule=None,
                        recurrence_id=occ_norm.isoformat(),
                    )
                    active.append(instance)

        return active

    @property
    def event(self) -> DanthermCalendarEvent | None:
        """Return the next ongoing or upcoming event, considering overrides and EXDATEs."""
        now = ha_now()
        upcoming: list[DanthermCalendarEvent] = []

        # 1) Check currently active — prioritize present
        for evt in self._events:
            dur = duration_dt(evt.start, evt.end)
            is_all_day = isinstance(evt.start, date) and not isinstance(
                evt.start, datetime
            )

            if not evt.rrule:
                start_dt = as_dt(evt.start)
                end_dt = as_dt(evt.end)
                if start_dt <= now < end_dt:
                    return evt
            else:
                rule = rrulestr(evt.rrule, dtstart=as_dt(evt.start))
                # Normalize EXDATEs to timezone-aware datetimes with zero microseconds
                # EXDATE can be provided as date or datetime; convert both via as_dt
                exdates = {as_dt(d).replace(microsecond=0) for d in (evt.exdate or [])}

                last_occ = rule.before(now, inc=True)
                if last_occ:
                    occ_norm = last_occ.replace(microsecond=0)
                    if occ_norm not in exdates:
                        # Use override if present
                        ovr = self._find_override(evt.uid, occ_norm)
                        if ovr:
                            st = as_dt(ovr.start)
                            en = as_dt(ovr.end)
                        elif is_all_day:
                            # Convert occurrence to its UTC calendar date, then map to local midnight
                            start_day = last_occ.astimezone(UTC).date()
                            days = max(1, int(dur.total_seconds() // 86400))
                            st = start_of_local_day(start_day)
                            en = start_of_local_day(start_day + timedelta(days=days))
                        else:
                            st = last_occ
                            en = last_occ + dur
                        if st <= now < en:
                            return DanthermCalendarEvent(
                                uid=evt.uid,
                                summary=ovr.summary if ovr else evt.summary,
                                start=st,
                                end=en,
                                description=(
                                    ovr.description if ovr else evt.description
                                ),
                                rrule=None,
                                recurrence_id=occ_norm.isoformat(),
                            )

        # 2) No active — find upcoming and select earliest
        window_end = now + timedelta(days=365)
        for evt in self._events:
            is_all_day = isinstance(evt.start, date) and not isinstance(
                evt.start, datetime
            )
            if not evt.rrule:
                if as_dt(evt.start) > now:
                    upcoming.append(evt)
            else:
                rule = rrulestr(evt.rrule, dtstart=as_dt(evt.start))
                # Normalize EXDATEs to timezone-aware datetimes with zero microseconds
                exdates = {as_dt(d).replace(microsecond=0) for d in (evt.exdate or [])}
                next_occ = rule.after(now, inc=False)
                while next_occ:
                    occ_norm = next_occ.replace(microsecond=0)
                    if occ_norm not in exdates:
                        ovr = self._find_override(evt.uid, occ_norm)
                        if ovr:
                            st = as_dt(ovr.start)
                            en = as_dt(ovr.end)
                            upcoming.append(
                                DanthermCalendarEvent(
                                    uid=evt.uid,
                                    summary=ovr.summary,
                                    start=st,
                                    end=en,
                                    description=ovr.description,
                                    rrule=None,
                                    recurrence_id=occ_norm.isoformat(),
                                )
                            )
                        else:
                            dur = duration_dt(evt.start, evt.end)
                            if is_all_day:
                                # Use the UTC calendar date of the occurrence to align to local day boundaries
                                start_day = next_occ.astimezone(UTC).date()
                                days = max(1, int(dur.total_seconds() // 86400))
                                st = start_of_local_day(start_day)
                                en = start_of_local_day(
                                    start_day + timedelta(days=days)
                                )
                            else:
                                st = next_occ
                                en = next_occ + dur
                            upcoming.append(
                                DanthermCalendarEvent(
                                    uid=evt.uid,
                                    summary=evt.summary,
                                    start=st,
                                    end=en,
                                    description=evt.description,
                                    rrule=None,
                                    recurrence_id=occ_norm.isoformat(),
                                )
                            )
                        break
                    # Skip exdated occurrence and look for the next one
                    next_occ = rule.after(occ_norm, inc=False)
                    if next_occ and next_occ >= window_end:
                        break

        if upcoming:
            upcoming.sort(key=lambda e: as_dt(e.start))
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
        data = [evt.to_json() for evt in self._events]
        await self._store.async_save(data)

    async def _load_events(self) -> None:
        """Load events from storage.

        Corrupt entries are skipped with a warning instead of breaking setup.
        """
        raw = await self._store.async_load() or []
        events: list[DanthermCalendarEvent] = []
        for idx, evt in enumerate(raw):
            try:
                start_v = parse_dt_or_date(evt.get("start"))
                end_v = parse_dt_or_date(evt.get("end"))
                all_day = evt.get("all_day")
                exdate = evt.get("exdate") or []

                # Drop obviously invalid time ranges
                if as_dt(end_v) <= as_dt(start_v):
                    _LOGGER.warning(
                        "Skipping event %s with invalid time range", evt.get("uid")
                    )
                    continue

                events.append(
                    DanthermCalendarEvent(
                        uid=evt.get("uid"),
                        summary=evt.get("summary", ""),
                        start=start_v,
                        end=end_v,
                        description=evt.get("description", ""),
                        rrule=evt.get("rrule"),
                        recurrence_id=evt.get("recurrence_id"),
                        exdate=exdate,
                        all_day=all_day,
                    )
                )
            except Exception:  # noqa: BLE001
                # keep calendar resilient to storage issues
                _LOGGER.warning("Skipping corrupt calendar entry at index %s", idx)
                continue
        self._events = events

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup references on removal."""
        await super().async_will_remove_from_hass()

        domain_data = self._hass.data.get(DOMAIN, {})
        # Remove global pointer if it points to this instance
        if domain_data.get(ATTR_CALENDAR) is self:
            domain_data.pop(ATTR_CALENDAR, None)


class DanthermCalendarEvent(CalendarEvent):
    """CalendarEvent extended with exception dates (EXDATE)."""

    def __init__(
        self,
        *,
        uid: str,
        summary: str,
        start: datetime | date,
        end: datetime | date,
        description: str = "",
        rrule: str | None = None,
        recurrence_id: str | None = None,
        exdate: list[datetime | date | str] | None = None,
        all_day: bool | None = None,
    ) -> None:
        """Initialize a calendar event with exception dates."""
        # Preserve date for all-day; normalize datetimes only
        start_parsed = parse_dt_or_date(start)
        end_parsed = parse_dt_or_date(end)

        # Detect all_day if not explicitly provided
        if all_day is None:
            all_day = isinstance(start_parsed, date) and not isinstance(
                start_parsed, datetime
            )

        if not all_day:
            # Normalize datetimes to timezone-aware, strip microseconds
            if isinstance(start_parsed, datetime):
                start_parsed = start_parsed.astimezone(ha_now().tzinfo).replace(
                    microsecond=0
                )
            if isinstance(end_parsed, datetime):
                end_parsed = end_parsed.astimezone(ha_now().tzinfo).replace(
                    microsecond=0
                )

        super().__init__(
            uid=uid,
            summary=summary,
            start=start_parsed,
            end=end_parsed,
            description=description,
            rrule=rrule,
            recurrence_id=recurrence_id,
        )

        # Normalize EXDATEs to datetimes (series use timed instances for exdates)
        self.exdate: list[datetime] = []
        if exdate:
            for v in exdate:
                pv = parse_dt_or_date(v)
                if isinstance(pv, date) and not isinstance(pv, datetime):
                    # Treat date exdates as midnight local
                    pv = datetime.combine(pv, datetime.min.time()).astimezone(
                        ha_now().tzinfo
                    )
                if isinstance(pv, datetime):
                    self.exdate.append(pv.replace(microsecond=0))

    def to_json(self) -> dict[str, Any]:
        """Convert the event to a JSON-friendly dictionary."""

        def encode(v: datetime | date | None) -> str | None:
            if v is None:
                return None
            if isinstance(v, datetime):
                return v.isoformat()
            # date-only
            return v.isoformat()

        # Derive all_day from types
        all_day_derived = isinstance(self.start, date) and not isinstance(
            self.start, datetime
        )

        return {
            "uid": self.uid,
            "summary": self.summary,
            "start": encode(self.start),
            "end": encode(self.end),
            "description": self.description,
            "rrule": self.rrule,
            "recurrence_id": self.recurrence_id,
            "exdate": [dt.isoformat() for dt in self.exdate],
            "all_day": all_day_derived,
        }
