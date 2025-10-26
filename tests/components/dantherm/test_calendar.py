"""Tests for Dantherm calendar entity behavior."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from config.custom_components.dantherm import (
    calendar as calendar_mod,
    translations as translations_mod,
)
from config.custom_components.dantherm.calendar import DanthermCalendar
from config.custom_components.dantherm.device_map import CALENDAR as CALENDAR_DESC
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

    async def _fake_async_get_adaptive_state_from_text(hass: HomeAssistant, text: str):
        return str(text).lower()

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_text",
        _fake_async_get_adaptive_state_from_text,
    )
    # Also patch the direct import in calendar module
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_text",
        _fake_async_get_adaptive_state_from_text,
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
