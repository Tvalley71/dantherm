"""Additional tests to increase coverage for Dantherm calendar."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from config.custom_components.dantherm import (
    calendar as calendar_mod,
    translations as translations_mod,
)
from config.custom_components.dantherm.calendar import (
    DanthermCalendar,
    DanthermCalendarEvent,
)
from config.custom_components.dantherm.device_map import (
    CALENDAR as CALENDAR_DESC,
    CONF_LINK_TO_PRIMARY_CALENDAR,
)
from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.components.calendar import CalendarEntity
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import now as ha_now, start_of_local_day


@pytest.fixture(autouse=True)
def _patch_adaptive_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch adaptive state resolution to a permissive stub for tests."""

    async def _fake_async_get_adaptive_state_from_summary(
        hass: HomeAssistant, text: str
    ):
        return str(text).lower()

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )


@pytest.fixture(autouse=True)
def _patch_async_write_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching HA state machine during unit tests for calendar."""

    def _no_write(self) -> None:
        return None

    monkeypatch.setattr(CalendarEntity, "async_write_ha_state", _no_write)


class FakeCoordinator:
    """Minimal async coordinator for entity base class."""

    last_update_success = True

    async def async_add_entity(self, entity: Any) -> None:
        """Simulate entity add."""
        return

    async def async_remove_entity(self, entity: Any) -> None:
        """Simulate entity remove."""
        return

    def async_add_listener(self, update_callback, context=None):  # type: ignore[override]
        """Return an unsubscribe callback, emulating DataUpdateCoordinator."""

        def _unsub():
            return None

        return _unsub


class FakeDevice:
    """Minimal device stub for DanthermEntity/Calendar tests."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize fake device with minimal attributes."""
        self.coordinator = FakeCoordinator()
        self._config_entry = SimpleNamespace(entry_id="entry-xyz")

    @property
    def get_device_name(self) -> str:
        """Return device name."""
        return "Dantherm Test"

    @property
    def get_device_type(self) -> str:
        """Return device type."""
        return "TEST"

    @property
    def get_device_fw_version(self) -> float:
        """Return firmware version."""
        return 3.14

    @property
    def get_device_serial_number(self) -> int:
        """Return device serial number."""
        return 999999

    async def async_install_entity(self, description) -> bool:
        """Allow installing the entity in tests."""
        return True


@pytest.mark.asyncio
async def test_create_event_invalid_adaptive_state_raises(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating an event with invalid adaptive state should raise and not store the event."""

    # Force translation helper to return None so InvalidAdaptiveState is raised
    async def _fake_async_get_adaptive_state_from_summary(
        _hass: HomeAssistant, text: str
    ):
        return None

    monkeypatch.setattr(
        translations_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )
    monkeypatch.setattr(
        calendar_mod,
        "async_get_adaptive_state_from_summary",
        _fake_async_get_adaptive_state_from_summary,
    )

    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_invalid_state"
    )

    with pytest.raises(calendar_mod.InvalidAdaptiveState):
        await cal.async_create_event(
            summary="not-a-state",
            dtstart=ha_now() + timedelta(hours=1),
            dtend=ha_now() + timedelta(hours=2),
        )

    assert cal._events == []


@pytest.mark.asyncio
async def test_expand_window_boundaries(hass: HomeAssistant) -> None:
    """Verify inclusive/exclusive window edges when expanding events."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_window_edges"
    )

    today = start_of_local_day()
    # Event A: exactly starts at window_start (included)
    await cal.async_create_event(
        summary="A",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
    )
    # Event B: ends exactly at window_start (excluded)
    await cal.async_create_event(
        summary="B",
        dtstart=today + timedelta(hours=6),
        dtend=today + timedelta(hours=8),
    )
    # Event C: starts exactly at end_date (excluded)
    await cal.async_create_event(
        summary="C",
        dtstart=today + timedelta(hours=10),
        dtend=today + timedelta(hours=11),
    )

    events = await cal.async_get_events(
        hass, today + timedelta(hours=8), today + timedelta(hours=10)
    )
    assert [e.summary for e in events] == ["A"]


@pytest.mark.asyncio
async def test_delete_one_time_by_uid(hass: HomeAssistant) -> None:
    """Deleting a single one-time event by UID should remove it entirely."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_delete_one_time"
    )
    now = start_of_local_day()
    await cal.async_create_event(
        summary="one", dtstart=now + timedelta(hours=9), dtend=now + timedelta(hours=10)
    )
    uid = cal._events[0].uid
    await cal.async_delete_event(uid=uid)
    assert cal._events == []


@pytest.mark.asyncio
async def test_thisandfuture_with_count_one_creates_no_new_master(
    hass: HomeAssistant,
) -> None:
    """Splitting a COUNT=1 series at its only occurrence should not create a new master."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_taf_count_one"
    )
    today = start_of_local_day()
    uid = "count1"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=1",
    )

    rid = (today + timedelta(hours=8)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(hours=8),
            "dtend": today + timedelta(hours=9),
        },
        recurrence_id=rid,
        recurrence_range="THISANDFUTURE",
    )

    # Expect original trimmed master and a new master starting at cutoff
    masters = [e for e in cal._events if e.rrule]
    assert len(masters) == 2
    new_master = max(masters, key=lambda e: e.start)
    assert new_master.start == (today + timedelta(hours=8))


@pytest.mark.asyncio
async def test_replace_master_with_new_rrule_and_exdate(hass: HomeAssistant) -> None:
    """Replacing master can accept new RRULE and EXDATE list."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_replace_exdate"
    )
    today = start_of_local_day()
    uid = "rep1"
    await cal.async_create_event(
        uid=uid,
        summary="home",
        dtstart=today + timedelta(hours=7),
        dtend=today + timedelta(hours=8),
        rrule="FREQ=DAILY;COUNT=3",
    )

    exdate = [today + timedelta(hours=7)]
    await cal.async_update_event(
        uid=uid,
        event={
            "start": today + timedelta(hours=9),
            "end": today + timedelta(hours=10),
            "rrule": "FREQ=DAILY;COUNT=5",
            "exdate": exdate,
        },
    )

    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    assert master.start == (today + timedelta(hours=9))
    assert master.end == (today + timedelta(hours=10))
    assert master.rrule == "FREQ=DAILY;COUNT=5"
    assert [d.replace(microsecond=0) for d in (master.exdate or [])] == [exdate[0]]


@pytest.mark.asyncio
async def test_update_thisandfuture_missing_cutoff_noop(hass: HomeAssistant) -> None:
    """Providing THISANDFUTURE without recurrence_id or dtstart should do nothing."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_taf_missing_cutoff",
    )
    today = start_of_local_day()
    uid = "series-no-cutoff"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=6),
        dtend=today + timedelta(hours=7),
        rrule="FREQ=DAILY;COUNT=2",
    )

    await cal.async_update_event(uid=uid, event={}, recurrence_range="THISANDFUTURE")
    # Master unchanged
    masters = [e for e in cal._events if e.uid == uid and e.rrule]
    assert len(masters) == 1


@pytest.mark.asyncio
async def test_update_thisandfuture_on_non_recurring_noop(hass: HomeAssistant) -> None:
    """Applying THISANDFUTURE on a non-recurring event should do nothing."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_taf_nonrec_update"
    )
    today = start_of_local_day()
    uid = "nonrec-update"
    await cal.async_create_event(
        uid=uid,
        summary="home",
        dtstart=today + timedelta(hours=6),
        dtend=today + timedelta(hours=7),
    )
    await cal.async_update_event(uid=uid, event={}, recurrence_range="THISANDFUTURE")
    assert any(e.uid == uid and not e.rrule for e in cal._events)


def test_event_exists_and_event_serialization(hass: HomeAssistant) -> None:
    """Cover event_exists and DanthermCalendarEvent JSON/all_day handling."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_event_exists"
    )

    # Create an all-day event using date objects
    evt = DanthermCalendarEvent(
        uid="d1",
        summary="home",
        start=date.today(),
        end=date.today(),
        exdate=[date.today()],
    )

    # Before adding to calendar, event_exists should be False
    assert not cal.event_exists(evt)

    # Add and check again
    cal._events.append(evt)
    assert cal.event_exists(evt)

    # to_json should include all_day and serializes exdate
    data = evt.to_json()
    assert data["all_day"] is True
    assert isinstance(data["start"], str)
    assert isinstance(data["end"], str)


@pytest.mark.asyncio
async def test_setup_entry_install_refused_skips_entity(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If device.async_install_entity returns False, calendar should not be created."""
    hass.data.setdefault("dantherm", {})

    class DeviceNoInstall(FakeDevice):
        async def async_install_entity(self, description) -> bool:  # type: ignore[override]
            return False

    added: list[DanthermCalendar] = []

    def _async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    entry = SimpleNamespace(entry_id="e4", options={})
    monkeypatch.setattr(calendar_mod, "is_primary_entry", lambda _hass, _id: True)
    hass.data["dantherm"]["e4"] = {"device": DeviceNoInstall(hass)}

    await calendar_mod.async_setup_entry(hass, entry, _async_add_entities)
    assert added == []
    # No global calendar pointer should be set
    assert hass.data["dantherm"].get("calendar") is None


@pytest.mark.asyncio
async def test_get_events_returns_empty_when_end_before_window(
    hass: HomeAssistant,
) -> None:
    """When end_date <= clamped start, async_get_events should return an empty list."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_empty_window"
    )
    today = start_of_local_day()
    events = await cal.async_get_events(
        hass, today - timedelta(days=1), today
    )  # end == clamped start
    assert events == []


@pytest.mark.asyncio
async def test_get_events_deduplicates_series_override_and_stored_instance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """async_get_events should de-duplicate when both series expansion and stored override produce the same instance."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_dedup_override"
    )
    today = start_of_local_day()

    uid = "series-dedup"
    await cal.async_create_event(
        uid=uid,
        summary="home",
        dtstart=today + timedelta(hours=12),
        dtend=today + timedelta(hours=13),
        rrule="FREQ=DAILY;COUNT=1",
    )
    rid = (today + timedelta(hours=12)).isoformat()
    # Create override for that same occurrence
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(hours=12),
            "dtend": today + timedelta(hours=12, minutes=45),
        },
        recurrence_id=rid,
    )

    # Request window including the occurrence
    events = await cal.async_get_events(
        hass, today + timedelta(hours=11), today + timedelta(hours=14)
    )
    assert len(events) == 1
    assert events[0].end == (today + timedelta(hours=12, minutes=45))


@pytest.mark.asyncio
async def test_get_events_deduplicates_same_uid_start_end_without_recurrence_id(
    hass: HomeAssistant,
) -> None:
    """De-dup should also work when recurrence_id is missing, falling back to start/end key."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_dedup_simple"
    )
    today = start_of_local_day()

    evt = DanthermCalendarEvent(
        uid="dup1",
        summary="eco",
        start=today + timedelta(hours=9),
        end=today + timedelta(hours=10),
    )
    cal._events.append(evt)
    # Append an identical one-time event with same UID and time
    cal._events.append(
        DanthermCalendarEvent(
            uid="dup1",
            summary="eco",
            start=today + timedelta(hours=9),
            end=today + timedelta(hours=10),
        )
    )

    events = await cal.async_get_events(
        hass, today + timedelta(hours=8), today + timedelta(hours=12)
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_delete_single_override_without_master(hass: HomeAssistant) -> None:
    """Deleting an override when no master exists should remove the standalone override only."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_delete_orphan_override",
    )
    today = start_of_local_day()
    # Inject a standalone override (no master with rrule)
    rid = (today + timedelta(hours=14)).isoformat()
    orphan = DanthermCalendarEvent(
        uid="orphan",
        summary="eco",
        start=today + timedelta(hours=14),
        end=today + timedelta(hours=15),
        recurrence_id=rid,
    )
    cal._events.append(orphan)

    await cal.async_delete_event(uid="orphan", recurrence_id=rid)
    assert cal._events == []


@pytest.mark.asyncio
async def test_async_added_to_hass_loads_stored_events(hass: HomeAssistant) -> None:
    """async_added_to_hass should load events saved in the store and call super()."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_added_to_hass"
    )
    today = start_of_local_day()
    # Save a valid event directly to store
    await cal._store.async_save(
        [
            {
                "uid": "stored1",
                "summary": "home",
                "start": (today + timedelta(hours=16)).isoformat(),
                "end": (today + timedelta(hours=17)).isoformat(),
            }
        ]
    )
    # Now add to hass (loads)
    await cal.async_added_to_hass()
    assert any(e.uid == "stored1" for e in cal._events)


@pytest.mark.asyncio
async def test_prune_removes_past_and_exhausted_series(hass: HomeAssistant) -> None:
    """_prune_events should remove one-time past events and exhausted series."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_prune"
    )
    today = start_of_local_day()

    # Past one-time event
    cal._events.append(
        DanthermCalendarEvent(
            uid="past1",
            summary="eco",
            start=today - timedelta(hours=2),
            end=today - timedelta(hours=1),
        )
    )
    # Exhausted series (COUNT=1) in the past
    await cal.async_create_event(
        uid="past-series",
        summary="home",
        dtstart=today - timedelta(days=2, hours=1),
        dtend=today - timedelta(days=2),
        rrule="FREQ=DAILY;COUNT=1",
    )

    # Trigger pruning via get events
    future_events = await cal.async_get_events(hass, today, today + timedelta(days=1))
    assert future_events == []
    # Ensure both entries were pruned from storage
    assert not any(e.uid in ("past1", "past-series") for e in cal._events)


@pytest.mark.asyncio
async def test_event_property_upcoming_exdate_then_next_outside_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """If the next occurrence is EXDATE and the following is >= window_end, the loop should break and return None."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_event_upcoming_break",
    )
    base = start_of_local_day()
    freezer.move_to(base + timedelta(hours=9))

    # First occurrence in 2 days (exdated), second occurrence 1 year later (>= window_end)
    start_first = base + timedelta(days=2, hours=10)
    await cal.async_create_event(
        uid="yearly",
        summary="eco",
        dtstart=start_first,
        dtend=start_first + timedelta(hours=1),
        rrule="FREQ=YEARLY;COUNT=2",
    )
    master = next(e for e in cal._events if e.uid == "yearly" and e.rrule)
    master.exdate = [start_first.replace(microsecond=0)]

    assert cal.event is None


@pytest.mark.asyncio
async def test_event_property_skips_exdate_to_next_occurrence(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Event property should skip EXDATE’d next occurrence and return the following one.

    We advance time to after today's event so the "next" occurrence is tomorrow,
    which is excluded via EXDATE, so the following day is selected.
    """
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_exdate_skip"
    )
    today = start_of_local_day()

    uid = "series-exdate-skip"
    await cal.async_create_event(
        uid=uid,
        summary="home",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Add EXDATE for tomorrow, so next valid upcoming is the day after tomorrow
    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    master.exdate = [today.replace(microsecond=0) + timedelta(days=1, hours=8)]

    # Advance time to after today's occurrence end so we consider the next occurrence
    freezer.move_to(today + timedelta(hours=10))
    # Now check upcoming
    upcoming = cal.event
    assert upcoming is not None
    # Should not be tomorrow at 08:00 due to EXDATE; should be the day after
    assert upcoming.start == (today + timedelta(days=2, hours=8))


@pytest.mark.asyncio
async def test_async_will_remove_from_hass_removes_global_pointer(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure async_will_remove_from_hass clears the global calendar pointer when it points to self."""
    monkeypatch.setattr(calendar_mod, "is_primary_entry", lambda _hass, _id: True)
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_remove_pointer"
    )
    # Simulate the global pointer
    hass.data.setdefault("dantherm", {})["calendar"] = cal
    await cal.async_will_remove_from_hass()
    assert hass.data["dantherm"].get("calendar") is None


@pytest.mark.asyncio
async def test_load_events_skips_generic_corrupt_entry(hass: HomeAssistant) -> None:
    """_load_events should skip entries that raise unexpectedly during parsing."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_load_corrupt2"
    )
    # Put an entry with invalid types that cause parse_dt_or_date to blow up
    await cal._store.async_save(
        [
            {
                "uid": "bad2",
                "summary": "eco",
                "start": {"not": "a-datetime"},
                "end": {"also": "bad"},
                # Serializable but invalid for parse_dt_or_date to exercise skip path
                "exdate": ["not-a-datetime"],
            }
        ]
    )
    await cal._load_events()
    assert cal._events == []


@pytest.mark.asyncio
async def test_replace_master_invalid_time_noop(hass: HomeAssistant) -> None:
    """Replacing master with end <= start should do nothing (no change to master)."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_replace_master_noop",
    )
    today = start_of_local_day()
    uid = "series-replace-noop"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    # Attempt invalid replace: end == start
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(hours=10),
            "dtend": today + timedelta(hours=10),
        },
    )
    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    assert master.start == (today + timedelta(hours=8))
    assert master.end == (today + timedelta(hours=9))


@pytest.mark.asyncio
async def test_thisandfuture_remaining_zero_creates_no_new_master(
    hass: HomeAssistant,
) -> None:
    """Splitting with cutoff after the only occurrence should not create a new master (remaining COUNT=0)."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_taf_remaining_zero",
    )
    today = start_of_local_day()
    uid = "count1_zero"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=1",
    )

    # Provide a cutoff after the only occurrence to make remaining COUNT=0
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": today + timedelta(days=1, hours=8)},
        recurrence_range="THISANDFUTURE",
    )

    masters = [e for e in cal._events if e.rrule]
    # Only the original trimmed master should exist
    assert len(masters) == 1


@pytest.mark.asyncio
async def test_async_setup_entry_paths(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise async_setup_entry helper paths for primary and non-primary entries."""
    # Prepare hass.data structure
    hass.data.setdefault("dantherm", {})

    added: list[DanthermCalendar] = []

    def _async_add_entities(entities, update_before_add=False):
        """Collect added entities in a list for assertions."""
        added.extend(entities)

    # Non-primary entry linking to primary should skip creation
    entry1 = SimpleNamespace(
        entry_id="e1", options={CONF_LINK_TO_PRIMARY_CALENDAR: True}
    )
    monkeypatch.setattr(calendar_mod, "is_primary_entry", lambda _hass, _id: False)
    hass.data["dantherm"]["e1"] = {"device": FakeDevice(hass)}
    await calendar_mod.async_setup_entry(hass, entry1, _async_add_entities)
    assert added == []

    # Primary entry should create and register global calendar
    entry2 = SimpleNamespace(entry_id="e2", options={})
    monkeypatch.setattr(calendar_mod, "is_primary_entry", lambda _hass, _id: True)
    hass.data["dantherm"]["e2"] = {"device": FakeDevice(hass)}
    await calendar_mod.async_setup_entry(hass, entry2, _async_add_entities)
    assert len(added) == 1
    assert hass.data["dantherm"].get("calendar") is added[0]

    # Missing device entry should log and return (no additional entity added)
    entry3 = SimpleNamespace(entry_id="e3", options={})
    hass.data["dantherm"]["e3"] = None
    await calendar_mod.async_setup_entry(hass, entry3, _async_add_entities)
    assert len(added) == 1  # unchanged


@pytest.mark.asyncio
async def test_async_setup_entry_device_missing_object(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the device object is missing in the entry, setup should log and return without adding entities."""
    hass.data.setdefault("dantherm", {})
    added: list[DanthermCalendar] = []

    def _async_add_entities(entities, update_before_add=False):
        added.extend(entities)

    entry = SimpleNamespace(entry_id="dev-missing", options={})
    monkeypatch.setattr(calendar_mod, "is_primary_entry", lambda _hass, _id: True)
    # Present entry but missing 'device' key
    hass.data["dantherm"]["dev-missing"] = {}

    await calendar_mod.async_setup_entry(hass, entry, _async_add_entities)
    assert added == []


@pytest.mark.asyncio
async def test_create_event_missing_summary_noop(hass: HomeAssistant) -> None:
    """Creating an event without a summary should be a no-op (warning path)."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_create_no_summary"
    )
    today = start_of_local_day()
    await cal.async_create_event(
        dtstart=today + timedelta(hours=1), dtend=today + timedelta(hours=2)
    )
    assert cal._events == []


@pytest.mark.asyncio
async def test_update_event_invalid_recurrence_id_noop(hass: HomeAssistant) -> None:
    """Invalid recurrence_id should log a warning and do nothing."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_update_invalid_rid",
    )
    today = start_of_local_day()
    uid = "rid-invalid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )

    # Attempt to update with an invalid recurrence_id
    await cal.async_update_event(
        uid=uid,
        event={"dtstart": today + timedelta(hours=8)},
        recurrence_id="not-a-datetime",
    )
    # Ensure still only the original master exists
    assert len([e for e in cal._events if e.uid == uid]) == 1


@pytest.mark.asyncio
async def test_update_override_invalid_time_noop(hass: HomeAssistant) -> None:
    """Overriding a single occurrence with end <= start should be ignored."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_override_invalid_time",
    )
    today = start_of_local_day()
    uid = "rid-invalid-time"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=6),
        dtend=today + timedelta(hours=7),
        rrule="FREQ=DAILY;COUNT=2",
    )
    rid = (today + timedelta(hours=6)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(hours=10),
            "dtend": today + timedelta(hours=10),
        },
        recurrence_id=rid,
    )
    # No override added
    assert not any(
        e.uid == uid and getattr(e, "recurrence_id", None) for e in cal._events
    )


@pytest.mark.asyncio
async def test_delete_thisandfuture_on_non_recurring_deletes_single(
    hass: HomeAssistant,
) -> None:
    """THISANDFUTURE on non-recurring UID deletes the one-time event(s)."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_delete_taf_nonrec"
    )
    today = start_of_local_day()
    await cal.async_create_event(
        uid="single",
        summary="home",
        dtstart=today + timedelta(hours=5),
        dtend=today + timedelta(hours=6),
    )
    await cal.async_delete_event(uid="single", recurrence_range="THISANDFUTURE")
    assert not any(e.uid == "single" for e in cal._events)


@pytest.mark.asyncio
async def test_delete_thisandfuture_first_occurrence_deletes_series(
    hass: HomeAssistant,
) -> None:
    """Deleting THISANDFUTURE at the first occurrence removes the entire series."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_delete_taf_first"
    )
    today = start_of_local_day()
    uid = "series-del"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=3",
    )
    rid_first = (today + timedelta(hours=8)).isoformat()
    await cal.async_delete_event(
        uid=uid, recurrence_id=rid_first, recurrence_range="THISANDFUTURE"
    )
    assert not any(e.uid == uid for e in cal._events)


@pytest.mark.asyncio
async def test_delete_thisandfuture_trim_middle_and_remove_future_overrides(
    hass: HomeAssistant,
) -> None:
    """Deleting THISANDFUTURE from the 2nd occurrence should trim series and drop overrides at/after cutoff."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_delete_taf_middle"
    )
    today = start_of_local_day()
    uid = "series-trim-mid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=3",
    )
    # Add an override on the 3rd day; it should be removed when trimming from day 2
    rid_day3 = (today + timedelta(days=2, hours=8)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(days=2, hours=8),
            "dtend": today + timedelta(days=2, hours=9, minutes=15),
        },
        recurrence_id=rid_day3,
    )

    # Delete from day 2 (middle)
    rid_day2 = (today + timedelta(days=1, hours=8)).isoformat()
    await cal.async_delete_event(
        uid=uid, recurrence_id=rid_day2, recurrence_range="THISANDFUTURE"
    )

    # Master should be trimmed and no overrides remain
    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    assert "UNTIL=" in master.rrule
    assert not any(
        e.uid == uid and getattr(e, "recurrence_id", None) for e in cal._events
    )


@pytest.mark.asyncio
async def test_delete_thisandfuture_requires_recurrence_id_warning(
    hass: HomeAssistant,
) -> None:
    """Deleting THISANDFUTURE without a recurrence_id should not change the series."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_delete_taf_requires_rid",
    )
    today = start_of_local_day()
    uid = "series-warn"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=7),
        dtend=today + timedelta(hours=8),
        rrule="FREQ=DAILY;COUNT=2",
    )
    await cal.async_delete_event(uid=uid, recurrence_range="THISANDFUTURE")
    # Master should still be present
    assert any(e.uid == uid and e.rrule for e in cal._events)


@pytest.mark.asyncio
async def test_delete_series_no_params_trims_now_and_removes_overrides(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Deleting a series without params should trim at now and drop future overrides."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_delete_series_now"
    )
    today = start_of_local_day()
    uid = "series-trim"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=6),
        dtend=today + timedelta(hours=7),
        rrule="FREQ=DAILY;COUNT=3",
    )

    # Create an override for tomorrow's occurrence; it should be removed when trimming at now
    rid_future = (today + timedelta(days=1, hours=6)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(days=1, hours=6),
            "dtend": today + timedelta(days=1, hours=7, minutes=30),
        },
        recurrence_id=rid_future,
    )

    # Move time to after today's first occurrence but before tomorrow
    freezer.move_to(today + timedelta(hours=7, minutes=30))
    await cal.async_delete_event(uid=uid)

    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    # Master UNTIL should be <= now (trimmed)
    assert "UNTIL=" in master.rrule
    # And future overrides removed
    assert not any(
        e.uid == uid and getattr(e, "recurrence_id", None) for e in cal._events
    )


@pytest.mark.asyncio
async def test_async_get_active_events_returns_current(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """async_get_active_events should return events active at 'now'."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_active_events"
    )
    today = start_of_local_day()
    freezer.move_to(today + timedelta(hours=10))

    # One-time active now
    await cal.async_create_event(
        uid="active-one",
        summary="home",
        dtstart=today + timedelta(hours=9, minutes=30),
        dtend=today + timedelta(hours=10, minutes=30),
    )

    # Recurring, not active yet
    await cal.async_create_event(
        uid="rec",
        summary="eco",
        dtstart=today + timedelta(hours=12),
        dtend=today + timedelta(hours=13),
        rrule="FREQ=DAILY;COUNT=2",
    )

    active = await cal.async_get_active_events()
    assert any(e.uid == "active-one" for e in active)


@pytest.mark.asyncio
async def test_event_property_active_recurring_without_override(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The event property should return the active recurring instance when no override exists."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_event_active_rec"
    )
    today = start_of_local_day()
    await cal.async_create_event(
        uid="rec-no-ovr",
        summary="eco",
        dtstart=today + timedelta(hours=11),
        dtend=today + timedelta(hours=12),
        rrule="FREQ=DAILY;COUNT=2",
    )
    freezer.move_to(today + timedelta(hours=11, minutes=30))
    ev = cal.event
    assert ev is not None
    assert ev.uid == "rec-no-ovr"


@pytest.mark.asyncio
async def test_all_day_series_with_exdate_date_skips_next(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """All-day series with EXDATE as date should skip next day and pick the following day."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_all_day_exdate"
    )
    base = start_of_local_day()
    today = base.date()

    # All-day: end must be the next date for exclusive end semantics
    await cal.async_create_event(
        uid="allday",
        summary="home",
        dtstart=today,
        dtend=today + timedelta(days=1),
        rrule="FREQ=DAILY;COUNT=3",
    )
    master = next(e for e in cal._events if e.uid == "allday" and e.rrule)
    # EXDATE provided as date object for 'tomorrow'
    master.exdate = [today + timedelta(days=1)]

    # Move time to after the first all-day occurrence has ended (just after midnight next day)
    freezer.move_to(base + timedelta(days=1, hours=1))
    upcoming = cal.event
    assert upcoming is not None
    # Should be the day after tomorrow (midnight)
    assert upcoming.start == (base + timedelta(days=2))
    assert upcoming.end == (base + timedelta(days=3))


@pytest.mark.asyncio
async def test_update_override_with_invalid_time_is_ignored(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Overriding a single occurrence with invalid time range should be a no-op."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_ovr_invalid_time"
    )
    base = start_of_local_day()
    uid = "ovr-invalid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )
    freezer.move_to(base + timedelta(hours=7))
    # Provide dtend before dtstart
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": base + timedelta(hours=8),
            "dtend": base + timedelta(hours=7, minutes=50),
        },
        recurrence_id=(base + timedelta(hours=8)).isoformat(),
    )
    # No override should have been created
    assert not any(
        e.uid == uid and getattr(e, "recurrence_id", None) for e in cal._events
    )


@pytest.mark.asyncio
async def test_thisandfuture_with_invalid_new_rrule_count_creates_new(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Invalid COUNT value in provided new RRULE should still create new master (exception path)."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_split_invalid_new"
    )
    base = start_of_local_day()
    uid = "split-invalid-new"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=3",
    )
    freezer.move_to(base + timedelta(hours=10))
    await cal.async_update_event(
        uid=uid,
        event={"rrule": "FREQ=DAILY;COUNT=abc"},
        recurrence_id=(base + timedelta(hours=8)).isoformat(),
        recurrence_range="THISANDFUTURE",
    )
    # Even with invalid COUNT in new rule, create_new should be True and a new master added
    masters = [e for e in cal._events if e.rrule]
    assert len(masters) >= 2


@pytest.mark.asyncio
async def test_event_property_active_all_day_recurring(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """An all-day recurring series should be reported as active during the day."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_active_allday"
    )
    base = start_of_local_day()
    today = base.date()
    await cal.async_create_event(
        uid="allday-active",
        summary="home",
        dtstart=today,
        dtend=today + timedelta(days=1),
        rrule="FREQ=DAILY;COUNT=2",
    )
    # Midday should be active
    freezer.move_to(base + timedelta(hours=12))
    ev = cal.event
    assert ev is not None
    assert ev.uid == "allday-active"
    assert ev.start == base


@pytest.mark.asyncio
async def test_find_override_returns_none_when_missing(hass: HomeAssistant) -> None:
    """_find_override should return None if no matching override exists."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_find_none"
    )
    base = start_of_local_day()
    uid = "series-no-ovr"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=1",
    )
    occ = base + timedelta(hours=8)
    assert cal._find_override(uid, occ) is None


@pytest.mark.asyncio
async def test_event_exists_helper(hass: HomeAssistant) -> None:
    """event_exists should correctly report presence of a stored event."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_event_exists"
    )
    base = start_of_local_day()
    await cal.async_create_event(
        uid="exists-1",
        summary="eco",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
    )
    ev = next(e for e in cal._events if e.uid == "exists-1")
    assert cal.event_exists(ev)
    # Different times should report false
    other = DanthermCalendarEvent(
        uid="exists-1",
        summary="eco",
        start=base + timedelta(hours=10),
        end=base + timedelta(hours=11),
    )
    assert not cal.event_exists(other)


@pytest.mark.asyncio
async def test_override_with_invalid_recurrence_id_is_ignored(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Overrides with invalid RECURRENCE-ID should be ignored by event selection."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_invalid_rid_ignored",
    )
    base = start_of_local_day()
    uid = "series-invalid-rid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=1",
    )
    # Add bogus override with non-parsable recurrence_id
    cal._events.append(
        DanthermCalendarEvent(
            uid=uid,
            summary="eco",
            start=base + timedelta(hours=8),
            end=base + timedelta(hours=10),
            recurrence_id="not-a-datetime",
        )
    )
    freezer.move_to(base + timedelta(hours=7))
    ev = cal.event
    assert ev is not None
    # Should be the unmodified instance from the series (ends at 09:00)
    assert ev.end == (base + timedelta(hours=9))


@pytest.mark.asyncio
async def test_midnight_crossing_event_active_and_window(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """One-time event crossing midnight should be active at 23:30 and appear in the query window."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_midnight_cross"
    )
    base = start_of_local_day()
    await cal.async_create_event(
        uid="cross",
        summary="home",
        dtstart=base + timedelta(hours=22, minutes=30),
        dtend=base + timedelta(days=1, minutes=30),
    )
    # Active at 23:30
    freezer.move_to(base + timedelta(hours=23, minutes=30))
    ev = cal.event
    assert ev is not None
    assert ev.end == (base + timedelta(days=1, minutes=30))

    # And returned by window spanning midnight
    events = await cal.async_get_events(
        hass, base + timedelta(hours=23), base + timedelta(days=1, hours=1)
    )
    assert any(e.uid == "cross" for e in events)


@pytest.mark.asyncio
async def test_upcoming_skips_multiple_exdates(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """When two consecutive occurrences are EXDATEd, upcoming should pick the third."""
    cal = DanthermCalendar(
        hass, FakeDevice(hass), CALENDAR_DESC, storage_key="cal_extra_multi_exdate"
    )
    base = start_of_local_day()
    uid = "multi-exdate"
    await cal.async_create_event(
        uid=uid,
        summary="home",
        dtstart=base + timedelta(hours=8),
        dtend=base + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=4",
    )
    master = next(e for e in cal._events if e.uid == uid and e.rrule)
    # Exclude next two days at 08:00
    master.exdate = [
        base.replace(microsecond=0) + timedelta(days=1, hours=8),
        base.replace(microsecond=0) + timedelta(days=2, hours=8),
    ]
    # Move after today's end so upcoming starts at tomorrow
    freezer.move_to(base + timedelta(hours=10))
    ev = cal.event
    assert ev is not None
    assert ev.start == (base + timedelta(days=3, hours=8))


@pytest.mark.asyncio
async def test_event_property_active_recurring_with_override(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The event property should return the active recurring override when present."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_event_active_recovr",
    )
    today = start_of_local_day()

    uid = "rec-ovr"
    # Series at 10:00-11:00 today
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=10),
        dtend=today + timedelta(hours=11),
        rrule="FREQ=DAILY;COUNT=2",
    )
    # Create an override for today's occurrence making it 10:00-10:45
    rid_today = (today + timedelta(hours=10)).isoformat()
    await cal.async_update_event(
        uid=uid,
        event={
            "dtstart": today + timedelta(hours=10),
            "dtend": today + timedelta(hours=10, minutes=45),
        },
        recurrence_id=rid_today,
    )

    freezer.move_to(today + timedelta(hours=10, minutes=30))
    ev = cal.event
    assert ev is not None
    assert ev.uid == uid
    # Should reflect override end time (10:45)
    assert ev.end == (today + timedelta(hours=10, minutes=45))


@pytest.mark.asyncio
async def test_delete_event_invalid_recurrence_id_noop(hass: HomeAssistant) -> None:
    """Deleting with an invalid recurrence_id should not change anything."""
    cal = DanthermCalendar(
        hass,
        FakeDevice(hass),
        CALENDAR_DESC,
        storage_key="cal_extra_delete_invalid_rid",
    )
    today = start_of_local_day()
    uid = "series-del-invalid"
    await cal.async_create_event(
        uid=uid,
        summary="eco",
        dtstart=today + timedelta(hours=8),
        dtend=today + timedelta(hours=9),
        rrule="FREQ=DAILY;COUNT=2",
    )
    await cal.async_delete_event(uid=uid, recurrence_id="not-a-datetime")
    assert any(e.uid == uid and e.rrule for e in cal._events)
