"""Tests for Dantherm calendar entity behavior."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from freezegun import freeze_time

from config.custom_components.dantherm import (
    calendar as calendar_mod,
    translations as translations_mod,
)
from config.custom_components.dantherm.calendar import DanthermCalendar
from config.custom_components.dantherm.device_map import CALENDAR as CALENDAR_DESC
from config.custom_components.dantherm.exceptions import InvalidAdaptiveState
import pytest

from homeassistant.components.calendar import CalendarEntity
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import now as ha_now, start_of_local_day


class FakeCoordinator:
    """Minimal async coordinator for entity base class."""

    last_update_success = True

    async def async_add_entity(self, entity: Any) -> None:
        """Simulate adding an entity to the coordinator."""
        return

    async def async_remove_entity(self, entity: Any) -> None:
        """Simulate removing an entity from the coordinator."""
        return


@pytest.fixture(autouse=True)
def _patch_adaptive_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch adaptive state resolution to avoid translation dependency in tests."""

    async def _fake_async_get_adaptive_state_from_summary(
        hass: HomeAssistant, text: str
    ):
        return str(text).lower()

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )
    # Also patch the direct import in calendar module
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )


@pytest.fixture(autouse=True)
def _patch_async_write_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching Home Assistant state machine during unit tests for calendar."""

    def _no_write(self) -> None:  # synchronous no-op to match HA signature
        return None

    monkeypatch.setattr(CalendarEntity, "async_write_ha_state", _no_write)


class FakeDevice:
    """Minimal device stub exposing attributes used by DanthermEntity."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize fake device with a minimal coordinator and entry id."""
        self.coordinator = FakeCoordinator()
        self._config_entry = SimpleNamespace(entry_id="entry-123")

    # Device info properties used by entity
    @property
    def get_device_name(self) -> str:
        """Return device name."""
        return "Dantherm Test"

    @property
    def get_device_type(self) -> str:
        """Return device model/type."""
        return "TEST"

    @property
    def get_device_fw_version(self) -> float:
        """Return firmware version as float."""
        return 3.14

    @property
    def get_device_serial_number(self) -> int:
        """Return serial number used in unique_id."""
        return 424242

    # Calendar install gate; calendar.setup checks this via device.async_install_entity
    async def async_install_entity(self, description) -> bool:
        """Always allow installing the entity in tests."""
        return True


@pytest.mark.asyncio
async def test_create_and_get_events_basic(hass: HomeAssistant) -> None:
    """Create a simple event and fetch it within a window."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_basic"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = ha_now()
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)

    await cal.async_create_event(summary="home", dtstart=start, dtend=end)

    # Query for the window around the event
    events = await cal.async_get_events(
        hass, start - timedelta(minutes=30), end + timedelta(minutes=30)
    )
    assert len(events) == 1
    assert events[0].summary == "home"
    assert events[0].start == start.replace(microsecond=0)
    assert events[0].end == end.replace(microsecond=0)


@pytest.mark.asyncio
async def test_override_single_occurrence_adds_exdate(hass: HomeAssistant) -> None:
    """Override one occurrence in a daily recurring series and ensure EXDATE is set."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_override"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = start_of_local_day()
    uid = "series-1"
    # Create a daily series (3 days)
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=10),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Override the second day's occurrence
    rid = (now + timedelta(days=1, hours=8)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": now + timedelta(days=1, hours=9),
            "dtend": now + timedelta(days=1, hours=11),
        },
        recurrence_id=rid,
    )

    # Expand window across 3 days
    events = await cal.async_get_events(hass, now, now + timedelta(days=3))

    # There should be 3 instances; the middle one is the override (shifted by +1h)
    assert len(events) == 3
    mid = events[1]
    assert mid.recurrence_id is not None  # instance from series
    assert mid.start == (now + timedelta(days=1, hours=9))
    assert mid.end == (now + timedelta(days=1, hours=11))

    # Master event should have EXDATE for the overridden occurrence
    masters = [e for e in cal._events if e.uid == uid and e.rrule]
    assert masters
    master = masters[0]
    assert any(
        d.replace(microsecond=0) == (now + timedelta(days=1, hours=8))
        for d in master.exdate
    )


@pytest.mark.asyncio
async def test_thisandfuture_splits_series(hass: HomeAssistant) -> None:
    """Applying THISANDFUTURE splits an existing series and trims original RRULE."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_thisandfuture"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = start_of_local_day()
    uid = "series-2"
    # Daily for 5 days starting today at 8-9
    await cal.async_create_event(
        uid=uid,
        summary="boost",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=5",
    )

    cutoff = now + timedelta(days=2, hours=8)
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": cutoff, "dtend": cutoff + timedelta(hours=1)},
        recurrence_id=cutoff.isoformat(),
        recurrence_range="THISANDFUTURE",
    )

    # Expect two masters: old trimmed + new starting at cutoff
    masters = [e for e in cal._events if e.rrule]
    assert len(masters) == 2
    new_master = max(masters, key=lambda e: e.start)
    assert new_master.start == cutoff

    # Expanding 5 days should still yield 5 instances overall
    instances = await cal.async_get_events(hass, now, now + timedelta(days=7))
    # Duplicates aren't expected; ensure count remains 5
    assert len(instances) == 5


@pytest.mark.asyncio
async def test_delete_single_occurrence_adds_exdate(hass: HomeAssistant) -> None:
    """Delete one occurrence and verify EXDATE is added and instance disappears."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_delete_single"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = start_of_local_day()
    uid = "series-del-1"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=7),
        dtend=now + timedelta(hours=8),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Delete the second occurrence
    rid = (now + timedelta(days=1, hours=7)).isoformat()
    await cal.async_delete_event(uid=uid, recurrence_id=rid)

    # Expand over 3 days => only 2 instances remain
    events = await cal.async_get_events(hass, now, now + timedelta(days=3))
    assert len(events) == 2
    # Master must contain EXDATE for the removed instance
    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    assert any(
        d.replace(microsecond=0) == (now + timedelta(days=1, hours=7))
        for d in master.exdate
    )


@pytest.mark.asyncio
async def test_delete_thisandfuture_from_first_occurrence_deletes_series(
    hass: HomeAssistant,
) -> None:
    """Deleting THISANDFUTURE from the first occurrence removes entire series."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_delete_taf_first"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = start_of_local_day()
    uid = "series-del-2"
    await cal.async_create_event(
        uid=uid,
        summary="boost",
        dtstart=now + timedelta(hours=6),
        dtend=now + timedelta(hours=7),
        rrule="FREQ=DAILY;COUNT=3",
    )

    rid_first = (now + timedelta(hours=6)).isoformat()
    await cal.async_delete_event(
        uid=uid, recurrence_id=rid_first, recurrence_range="THISANDFUTURE"
    )

    events = await cal.async_get_events(hass, now, now + timedelta(days=7))
    assert events == []


@pytest.mark.asyncio
async def test_event_property_active_and_upcoming(hass: HomeAssistant) -> None:
    """Validate event property prioritizes current over upcoming and picks earliest upcoming."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_event_property"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = ha_now()
    # Upcoming in 2 hours
    await cal.async_create_event(
        summary="home", dtstart=now + timedelta(hours=2), dtend=now + timedelta(hours=3)
    )
    # Upcoming in 1 hour
    await cal.async_create_event(
        summary="eco",
        dtstart=now + timedelta(hours=1),
        dtend=now + timedelta(hours=1, minutes=30),
    )
    # Currently active
    await cal.async_create_event(
        summary="boost",
        dtstart=now - timedelta(minutes=5),
        dtend=now + timedelta(minutes=5),
    )

    # Should return the active one
    active = cal.event
    assert active is not None
    assert active.summary == "boost"

    # Remove the active, then earliest upcoming should be "eco"
    # Delete by exact UID and times by finding the matching stored event
    to_remove = next(e for e in cal._events if e.summary == "boost" and not e.rrule)
    await cal.async_delete_event(uid=to_remove.uid)

    upcoming = cal.event
    assert upcoming is not None
    assert upcoming.summary == "eco"


@pytest.mark.asyncio
async def test_sorting_order_of_events(hass: HomeAssistant) -> None:
    """Events should be returned in chronological order regardless of creation order."""
    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_sorting"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = start_of_local_day()

    # Create out of order: C (t+3h), A (t+1h), B (t+2h)
    await cal.async_create_event(
        summary="C", dtstart=now + timedelta(hours=3), dtend=now + timedelta(hours=4)
    )
    await cal.async_create_event(
        summary="A",
        dtstart=now + timedelta(hours=1),
        dtend=now + timedelta(hours=1, minutes=30),
    )
    await cal.async_create_event(
        summary="B",
        dtstart=now + timedelta(hours=2),
        dtend=now + timedelta(hours=2, minutes=30),
    )

    events = await cal.async_get_events(hass, now, now + timedelta(days=1))
    assert [e.summary for e in events] == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_create_event_missing_summary_noop(hass: HomeAssistant) -> None:
    """Creating an event without a summary should not add an event."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass,
        device,
        CALENDAR_DESC,
        storage_key="dantherm_calendar_test_missing_summary",
    )

    start = ha_now() + timedelta(hours=1)
    await cal.async_create_event(dtstart=start, dtend=start + timedelta(hours=1))

    # No events should have been added
    assert cal._events == []


@pytest.mark.asyncio
async def test_create_event_end_before_start_noop(hass: HomeAssistant) -> None:
    """Creating an event with end <= start should do nothing."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_bad_range"
    )

    start = ha_now() + timedelta(hours=2)
    await cal.async_create_event(
        summary="eco", dtstart=start, dtend=start - timedelta(minutes=1)
    )
    assert cal._events == []


@pytest.mark.asyncio
async def test_update_nonexistent_event_noop(hass: HomeAssistant) -> None:
    """Updating a non-existing UID should do nothing."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_update_missing"
    )

    await cal.async_update_event(
        uid="nope", event={"dtstart": ha_now(), "dtend": ha_now() + timedelta(hours=1)}
    )
    assert cal._events == []


@pytest.mark.asyncio
async def test_update_event_invalid_recurrence_id_noop(hass: HomeAssistant) -> None:
    """Invalid recurrence_id should not change the series."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_bad_rid"
    )

    now = start_of_local_day()
    uid = "series-bad-rid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    # Provide an invalid recurrence_id
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": now + timedelta(hours=9)},
        recurrence_id="not-a-datetime",
    )

    masters = [e for e in cal._events if e.uid == uid and e.rrule]
    assert len(masters) == 1


@pytest.mark.asyncio
async def test_thisandfuture_on_non_recurring_noop(hass: HomeAssistant) -> None:
    """Applying THISANDFUTURE to a non-recurring event should be ignored."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_taf_no_series"
    )

    now = start_of_local_day()
    await cal.async_create_event(
        summary="eco", dtstart=now + timedelta(hours=8), dtend=now + timedelta(hours=9)
    )
    one = cal._events[0]

    await cal.async_update_event(
        uid=one.uid,
        event={"dtstart": one.start},
        recurrence_id=now.isoformat(),
        recurrence_range="THISANDFUTURE",
    )
    # Still only one event, unchanged
    assert len(cal._events) == 1
    assert cal._events[0].rrule is None


@pytest.mark.asyncio
async def test_delete_thisandfuture_without_recurrence_id_noop(
    hass: HomeAssistant,
) -> None:
    """Deleting THISANDFUTURE without a recurrence_id should be ignored (warning only)."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_del_taf_no_rid"
    )

    now = start_of_local_day()
    uid = "series-del-taf"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    await cal.async_delete_event(uid=uid, recurrence_range="THISANDFUTURE")

    # Series remains intact
    masters = [e for e in cal._events if e.uid == uid and e.rrule]
    assert len(masters) == 1


@pytest.mark.asyncio
async def test_prune_removes_past_events_and_series(hass: HomeAssistant) -> None:
    """Prune should remove one-time past events and exhausted series."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_prune"
    )

    today = start_of_local_day()
    yesterday = today - timedelta(days=1)

    # Past one-time event
    await cal.async_create_event(
        summary="eco",
        dtstart=yesterday + timedelta(hours=8),
        dtend=yesterday + timedelta(hours=9),
    )

    # Series that only occurred yesterday
    await cal.async_create_event(
        uid="old-series",
        summary="boost",
        dtstart=yesterday + timedelta(hours=10),
        dtend=yesterday + timedelta(hours=11),
        rrule="FREQ=DAILY;COUNT=1",
    )

    # Trigger pruning by querying today window
    events_today = await cal.async_get_events(hass, today, today + timedelta(days=1))
    # None of the past items should remain or appear
    assert events_today == []
    # Stored events should also be pruned
    assert cal._events == []


@pytest.mark.asyncio
async def test_replace_master_updates_time_and_keeps_rrule(hass: HomeAssistant) -> None:
    """Replacing the master event should update start/end and retain the series RRULE by default."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_replace_master"
    )

    now = start_of_local_day()
    uid = "series-replace"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    # Replace master shifting by +1 hour
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": now + timedelta(hours=9), "dtend": now + timedelta(hours=10)},
    )

    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    assert master.start == (now + timedelta(hours=9))
    assert master.end == (now + timedelta(hours=10))
    assert master.rrule == "FREQ=DAILY;COUNT=2"

    # Expanded instances should reflect new time
    events = await cal.async_get_events(hass, now, now + timedelta(days=2))
    assert all(e.start.hour == 9 for e in events)


@pytest.mark.asyncio
async def test_override_invalid_time_range_noop(hass: HomeAssistant) -> None:
    """Overriding a single instance with invalid time range should be ignored and not add EXDATE."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass,
        device,
        CALENDAR_DESC,
        storage_key="dantherm_calendar_test_override_bad_range",
    )

    now = start_of_local_day()
    uid = "series-bad-override"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(hours=8),
        dtend=now + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    rid = (now + timedelta(hours=8)).isoformat()
    # Attempt override with end <= start
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": now + timedelta(hours=9), "dtend": now + timedelta(hours=9)},
        recurrence_id=rid,
    )

    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    # EXDATE should not contain the attempted override
    assert not any(
        d.replace(microsecond=0) == (now + timedelta(hours=8))
        for d in (master.exdate or [])
    )
    # No override entity created
    assert not any(
        e.uid == uid and getattr(e, "recurrence_id", None) == rid for e in cal._events
    )


@pytest.mark.asyncio
async def test_event_property_prefers_active_override(hass: HomeAssistant) -> None:
    """The event property should return an active override over the base instance when present."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass,
        device,
        CALENDAR_DESC,
        storage_key="dantherm_calendar_test_event_override_active",
    )

    now = ha_now()
    uid = "series-active-ovr"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now - timedelta(minutes=10),
        dtend=now + timedelta(minutes=10),
        rrule="FREQ=DAILY;COUNT=2",
    )

    # Override the current occurrence to a different summary; keep it active
    rid = (now - timedelta(minutes=10)).replace(microsecond=0).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "summary": "boost",
            "dtstart": now - timedelta(minutes=5),
            "dtend": now + timedelta(minutes=15),
        },
        recurrence_id=rid,
    )

    ev = cal.event
    assert ev is not None
    assert ev.summary == "boost"


@pytest.mark.asyncio
async def test_get_active_events_multiple(hass: HomeAssistant) -> None:
    """Active events API should return multiple overlapping active events."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_active_list"
    )

    now = ha_now()
    await cal.async_create_event(
        summary="A",
        dtstart=now - timedelta(minutes=2),
        dtend=now + timedelta(minutes=2),
    )
    await cal.async_create_event(
        summary="B",
        dtstart=now - timedelta(minutes=1),
        dtend=now + timedelta(minutes=1),
    )

    active = await cal.async_get_active_events()
    assert {e.summary for e in active} == {"A", "B"}


@pytest.mark.asyncio
async def test_delete_series_no_params_trims_future(hass: HomeAssistant) -> None:
    """Calling delete_event on a series without params should trim future so no instances remain after now."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass,
        device,
        CALENDAR_DESC,
        storage_key="dantherm_calendar_test_delete_series_trim",
    )

    now = ha_now()
    uid = "series-trim"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=now + timedelta(minutes=30),
        dtend=now + timedelta(minutes=60),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Delete with no params; since all occurrences are in the future, trimming removes them
    await cal.async_delete_event(uid=uid)
    events = await cal.async_get_events(hass, now, now + timedelta(days=7))
    assert events == []


@pytest.mark.asyncio
async def test_get_events_clamps_start_to_today(hass: HomeAssistant) -> None:
    """async_get_events should clamp start_date to today and still return today's events when start_date < today."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_clamp_start"
    )

    today = start_of_local_day()
    await cal.async_create_event(
        summary="today",
        dtstart=today + timedelta(hours=10),
        dtend=today + timedelta(hours=11),
    )

    events = await cal.async_get_events(
        hass, today - timedelta(days=1), today + timedelta(days=1)
    )
    assert len(events) == 1
    assert events[0].summary == "today"


@pytest.mark.asyncio
async def test_load_skips_corrupt_entries(hass: HomeAssistant) -> None:
    """_load_events should skip corrupt entries rather than raising."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="dantherm_calendar_test_load_corrupt"
    )

    # Manually write corrupt data: end <= start causes skip
    today = start_of_local_day()
    await cal._store.async_save(
        [
            {
                "uid": "bad",
                "summary": "eco",
                "start": (today + timedelta(hours=10)).isoformat(),
                "end": (today + timedelta(hours=9)).isoformat(),
                "description": "",
                "rrule": None,
                "recurrence_id": None,
                "exdate": [],
                "all_day": False,
            }
        ]
    )

    await cal._load_events()
    assert cal._events == []


@pytest.mark.asyncio
async def test_async_get_active_events_single_events(hass: HomeAssistant) -> None:
    """Test async_get_active_events with single (non-recurring) events."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_single"
    )

    now = ha_now()

    # Active event (started 10 minutes ago, ends in 10 minutes)
    await cal.async_create_event(
        summary="currently_active",
        dtstart=now - timedelta(minutes=10),
        dtend=now + timedelta(minutes=10),
    )

    # Future event (starts in 1 hour)
    await cal.async_create_event(
        summary="future_event",
        dtstart=now + timedelta(hours=1),
        dtend=now + timedelta(hours=2),
    )

    # Past event (ended 5 minutes ago)
    await cal.async_create_event(
        summary="past_event",
        dtstart=now - timedelta(hours=2),
        dtend=now - timedelta(minutes=5),
    )

    active_events = await cal.async_get_active_events()

    # Only the currently active event should be returned
    assert len(active_events) == 1
    assert active_events[0].summary == "currently_active"


@pytest.mark.asyncio
async def test_async_get_active_events_recurring_series(hass: HomeAssistant) -> None:
    """Test async_get_active_events with recurring events."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_recurring"
    )

    now = ha_now()

    # Daily recurring event that started yesterday and is currently active
    # (each occurrence lasts 2 hours, happens daily at the same time)
    daily_start = now - timedelta(minutes=30)  # Started 30 minutes ago
    await cal.async_create_event(
        uid="daily_series",
        summary="daily_active",
        dtstart=daily_start,
        dtend=daily_start + timedelta(hours=2),  # Ends in 1.5 hours
        rrule="FREQ=DAILY;COUNT=5",
    )

    # Weekly recurring event that's not currently active
    # (started 3 days ago, each occurrence lasts 1 hour)
    weekly_start = now - timedelta(days=3, hours=1)  # Ended 3 days ago
    await cal.async_create_event(
        uid="weekly_series",
        summary="weekly_inactive",
        dtstart=weekly_start,
        dtend=weekly_start + timedelta(hours=1),
        rrule="FREQ=WEEKLY;COUNT=3",
    )

    active_events = await cal.async_get_active_events()

    # Only the daily series should have an active occurrence
    assert len(active_events) == 1
    assert active_events[0].summary == "daily_active"
    assert active_events[0].recurrence_id is not None  # It's an instance


@pytest.mark.asyncio
async def test_async_get_active_events_with_overrides(hass: HomeAssistant) -> None:
    """Test async_get_active_events with recurring events that have overrides."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_overrides"
    )

    now = ha_now()
    uid = "series_with_override"

    # Create a daily series where current occurrence should be active
    series_start = now - timedelta(minutes=15)  # Started 15 minutes ago
    await cal.async_create_event(
        uid=uid,
        summary="original_summary",
        dtstart=series_start,
        dtend=series_start + timedelta(hours=1),  # Ends in 45 minutes
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Override today's occurrence with different timing and summary
    override_start = now - timedelta(minutes=5)  # Override started 5 minutes ago
    await cal.async_update_event(
        uid=uid,
        event={
            "summary": "overridden_summary",
            "dtstart": override_start,
            "dtend": override_start + timedelta(minutes=30),  # Ends in 25 minutes
        },
        recurrence_id=series_start.replace(microsecond=0).isoformat(),
    )

    active_events = await cal.async_get_active_events()

    # Should return the override, not the original occurrence
    assert len(active_events) == 1
    assert active_events[0].summary == "overridden_summary"
    assert active_events[0].start == override_start.replace(microsecond=0)


@pytest.mark.asyncio
async def test_async_get_active_events_with_exdates(hass: HomeAssistant) -> None:
    """Test async_get_active_events respects EXDATE exclusions."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_exdates"
    )

    now = ha_now()
    uid = "series_with_exdate"

    # Create a series where current time should have an active occurrence
    series_start = now - timedelta(minutes=20)
    await cal.async_create_event(
        uid=uid,
        summary="excluded_today",
        dtstart=series_start,
        dtend=series_start + timedelta(hours=1),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Delete today's occurrence (adds it to EXDATE)
    await cal.async_delete_event(
        uid=uid,
        recurrence_id=series_start.replace(microsecond=0).isoformat(),
    )

    active_events = await cal.async_get_active_events()

    # Should be empty because today's occurrence is excluded
    assert len(active_events) == 0


@pytest.mark.asyncio
async def test_async_get_active_events_multiple_active(hass: HomeAssistant) -> None:
    """Test async_get_active_events returns multiple overlapping active events."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_multiple"
    )

    now = ha_now()

    # Two overlapping single events
    await cal.async_create_event(
        summary="event_1",
        dtstart=now - timedelta(minutes=30),
        dtend=now + timedelta(minutes=30),
    )

    await cal.async_create_event(
        summary="event_2",
        dtstart=now - timedelta(minutes=15),
        dtend=now + timedelta(minutes=45),
    )

    # One recurring event with active occurrence
    await cal.async_create_event(
        uid="recurring_active",
        summary="recurring_event",
        dtstart=now - timedelta(minutes=10),
        dtend=now + timedelta(minutes=20),
        rrule="FREQ=DAILY;COUNT=2",
    )

    active_events = await cal.async_get_active_events()

    # Should return all 3 active events
    assert len(active_events) == 3
    summaries = {event.summary for event in active_events}
    assert summaries == {"event_1", "event_2", "recurring_event"}


@pytest.mark.asyncio
@freeze_time(
    "2025-11-02 12:00:00"
)  # Freeze time to midday to ensure all-day event is active
async def test_async_get_active_events_day_boundary_scenarios(
    hass: HomeAssistant,
) -> None:
    """Test async_get_active_events around day boundaries and timezone handling."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_boundaries"
    )

    # Get current time and day boundaries
    now = ha_now()
    today_start = start_of_local_day()

    # Create an all-day event for today
    await cal.async_create_event(
        summary="all_day_today",
        dtstart=today_start.date(),  # Pass as date for all-day
        dtend=(today_start + timedelta(days=1)).date(),
    )

    # Create a recurring series that started days ago but has active occurrence today
    old_start = today_start - timedelta(days=10, hours=2)  # 10 days ago

    # Calculate when today's occurrence would be based on the old start
    # For daily series, today's occurrence should be at the same time of day
    daily_series_start = today_start.replace(
        hour=old_start.hour,
        minute=old_start.minute,
        second=old_start.second,
        microsecond=0,
    )

    await cal.async_create_event(
        uid="old_daily_series",
        summary="daily_from_past",
        dtstart=old_start,
        dtend=old_start + timedelta(hours=3),
        rrule="FREQ=DAILY;COUNT=15",  # Enough to cover today
    )

    active_events = await cal.async_get_active_events()

    # Check if we have active events
    # The all-day event should be active throughout the day
    # The recurring event should be active if current time falls within its occurrence window
    active_summaries = {event.summary for event in active_events}

    # All-day event should always be active during the day
    assert "all_day_today" in active_summaries

    # Recurring event should be active if we're within its time window
    if daily_series_start <= now < daily_series_start + timedelta(hours=3):
        assert "daily_from_past" in active_summaries
    else:
        assert "daily_from_past" not in active_summaries


@pytest.mark.asyncio
async def test_async_get_active_events_long_running_series(hass: HomeAssistant) -> None:
    """Test async_get_active_events with series that started far in the past."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_long_running"
    )

    now = ha_now()

    # Create a series that started 6 months ago, occurs weekly, and should have an active occurrence now
    # Calculate a start time 6 months ago that would result in an active occurrence now
    months_ago = now - timedelta(days=180)  # Approximately 6 months

    # Adjust to create a weekly series where one occurrence is active right now
    # Find the most recent weekly occurrence before now
    weeks_since = (now - months_ago).days // 7

    # Adjust so the occurrence spans the current time
    adjusted_start = now - timedelta(minutes=30)  # Started 30 minutes ago
    original_start = adjusted_start - timedelta(weeks=weeks_since)

    await cal.async_create_event(
        uid="long_running_weekly",
        summary="weekly_from_months_ago",
        dtstart=original_start,
        dtend=original_start + timedelta(hours=2),  # 2-hour duration
        rrule="FREQ=WEEKLY;COUNT=50",  # Enough occurrences to reach today
    )

    active_events = await cal.async_get_active_events()

    # Should find the active occurrence from the long-running series
    assert len(active_events) == 1
    assert active_events[0].summary == "weekly_from_months_ago"
    assert active_events[0].recurrence_id is not None


@pytest.mark.asyncio
async def test_async_get_active_events_no_active_events(hass: HomeAssistant) -> None:
    """Test async_get_active_events returns empty list when no events are active."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key="test_active_none")

    now = ha_now()

    # Create events that are not currently active
    await cal.async_create_event(
        summary="future_event",
        dtstart=now + timedelta(hours=1),
        dtend=now + timedelta(hours=2),
    )

    await cal.async_create_event(
        summary="past_event",
        dtstart=now - timedelta(hours=2),
        dtend=now - timedelta(hours=1),
    )

    # Recurring series with no current active occurrence
    await cal.async_create_event(
        uid="inactive_series",
        summary="weekly_inactive",
        dtstart=now - timedelta(days=7, hours=1),  # Last week, ended
        dtend=now - timedelta(days=7),  # 1 hour duration, ended 7 days ago
        rrule="FREQ=WEEKLY;COUNT=2",
    )

    active_events = await cal.async_get_active_events()

    # Should return empty list
    assert active_events == []


@pytest.mark.asyncio
async def test_async_get_active_events_edge_case_exact_boundaries(
    hass: HomeAssistant,
) -> None:
    """Test async_get_active_events with events at exact start/end boundaries."""
    device = FakeDevice(hass)
    cal = DanthermCalendar(
        hass, device, CALENDAR_DESC, storage_key="test_active_boundaries_exact"
    )

    now = ha_now()

    # Event that starts exactly now
    await cal.async_create_event(
        summary="starts_now",
        dtstart=now,
        dtend=now + timedelta(hours=1),
    )

    # Event that ends exactly now (should not be active)
    await cal.async_create_event(
        summary="ends_now",
        dtstart=now - timedelta(hours=1),
        dtend=now,
    )

    active_events = await cal.async_get_active_events()

    # Only the event that starts now should be active (start <= now < end)
    assert len(active_events) == 1
    assert active_events[0].summary == "starts_now"


@pytest.mark.asyncio
async def test_create_event_invalid_adaptive_state(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that create_event validates adaptive states and shows available states in error."""

    # Patch to return None for invalid states
    async def _invalid_adaptive_state(hass: HomeAssistant, text: str):
        return None if text == "invalid_state" else str(text).lower()

    # Patch to return mock available states
    async def _mock_available_states(hass: HomeAssistant):
        return {"auto": "Auto", "komfort": "Komfort", "øko": "Øko"}

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_summary",
        _invalid_adaptive_state,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_summary",
        _invalid_adaptive_state,
    )
    monkeypatch.setattr(
        translations_mod,
        "async_get_available_adaptive_states",
        _mock_available_states,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_available_adaptive_states",
        _mock_available_states,
    )

    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_invalid_state"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = ha_now()
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)

    # Try to create event with invalid adaptive state
    with pytest.raises(InvalidAdaptiveState) as exc_info:
        await cal.async_create_event(summary="invalid_state", dtstart=start, dtend=end)

    # Check that the exception contains available states
    assert "invalid_state" in str(exc_info.value.translation_placeholders["state"])
    assert "Auto, Komfort, Øko" in str(
        exc_info.value.translation_placeholders["available_states"]
    )


@pytest.mark.asyncio
async def test_update_event_invalid_adaptive_state(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that update_event validates adaptive states and shows available states in error."""

    device = FakeDevice(hass)
    storage_key = "dantherm_calendar_test_update_invalid_state"
    cal = DanthermCalendar(hass, device, CALENDAR_DESC, storage_key=storage_key)

    now = ha_now()
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)

    # First create a valid event
    uid = "test-event-1"
    await cal.async_create_event(uid=uid, summary="auto", dtstart=start, dtend=end)

    # Now patch for invalid state during update
    async def _invalid_adaptive_state(hass: HomeAssistant, text: str):
        return None if text == "invalid_update_state" else str(text).lower()

    # Patch to return mock available states
    async def _mock_available_states(hass: HomeAssistant):
        return {"auto": "Auto", "komfort": "Komfort", "øko": "Øko"}

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_summary",
        _invalid_adaptive_state,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_summary",
        _invalid_adaptive_state,
    )
    monkeypatch.setattr(
        translations_mod,
        "async_get_available_adaptive_states",
        _mock_available_states,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_available_adaptive_states",
        _mock_available_states,
    )

    # Try to update event with invalid adaptive state
    with pytest.raises(InvalidAdaptiveState) as exc_info:
        await cal.async_update_event(uid=uid, event={"summary": "invalid_update_state"})

    # Check that the exception contains available states
    assert "invalid_update_state" in str(
        exc_info.value.translation_placeholders["state"]
    )
    assert "Auto, Komfort, Øko" in str(
        exc_info.value.translation_placeholders["available_states"]
    )
