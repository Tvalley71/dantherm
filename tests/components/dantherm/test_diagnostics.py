"""Diagnostics tests for Dantherm integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from config.custom_components.dantherm.calendar import DanthermCalendarEvent
from config.custom_components.dantherm.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from config.custom_components.dantherm.device_map import ATTR_CALENDAR
from config.custom_components.dantherm.diagnostics import (
    _extract_adaptive_state_async,
    async_get_config_entry_diagnostics,
)
import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_diagnostics_basic_structure_and_redaction(
    hass: HomeAssistant,
) -> None:
    """Validate diagnostics structure and redaction of sensitive fields."""
    # Create a config entry
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: "10.0.0.5",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        options={},
        unique_id="SERIAL-1",
        entry_id="entry-1",
    )
    entry.add_to_hass(hass)

    # Register a device and entity for the entry
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "device-123")},
        manufacturer="Dantherm",
        model="HCV300",
        name="Ventilation Unit",
        sw_version="3.10.0",
        hw_version="A",
    )

    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="uid-1",
        suggested_object_id="fan_level",
        config_entry=entry,
        device_id=device.id,
    )

    # Fake coordinator and device objects in runtime storage
    coordinator: DataUpdateCoordinator = SimpleNamespace(
        last_update_success=True,
        last_update_success_time=None,
        update_interval=30,
        data={"foo": 1, "bar": 2},
    )
    fake_device = SimpleNamespace(
        installed_components=0xFFFF,
        get_device_name="Ventilation Unit",
        get_device_type=1,
        get_device_fw_version="3.10.0",
        get_device_serial_number=123456789,
        get_features_attrs={"feature_a": True},
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device": fake_device,
        "coordinator": coordinator,
    }

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Entry basics
    assert diag["entry"]["entry_id"] == entry.entry_id
    assert diag["entry"]["title"] == DEFAULT_NAME
    # Redaction
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"

    # Device summary
    assert diag["device"]["id"] == device.id
    assert diag["device"]["manufacturer"] == "Dantherm"
    assert diag["device"]["model"] == "HCV300"

    # Entities list contains the one we created
    assert any(e["unique_id"] == "uid-1" for e in diag["entities"]) is True

    # Runtime includes coordinator snapshot with data keys
    assert diag["runtime"]["coordinator"]["last_update_success"] is True
    assert set(diag["runtime"]["coordinator"]["data_keys"]) == {"foo", "bar"}


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_diagnostics_handles_missing_device_and_runtime(
    hass: HomeAssistant,
) -> None:
    """Diagnostics should cope when no device is in registry and no runtime data is present."""
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={CONF_NAME: DEFAULT_NAME, CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
        options={},
        unique_id="SERIAL-2",
        entry_id="entry-2",
    )
    entry.add_to_hass(hass)

    # No device/entries created; also omit hass.data[DOMAIN][entry_id]
    hass.data.setdefault(DOMAIN, {})

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["device"] is None
    assert isinstance(diag["entities"], list)
    assert diag["runtime"] is None
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"


@pytest.mark.asyncio
async def test_extract_adaptive_state_async(hass: HomeAssistant) -> None:
    """Test the async adaptive state extraction function with real translations."""
    # Mock the async_get_adaptive_state_from_summary function to return known states
    with patch(
        "config.custom_components.dantherm.diagnostics.async_get_adaptive_state_from_summary"
    ) as mock_get_state:
        # Test various adaptive state patterns
        mock_get_state.return_value = "level_2"
        result = await _extract_adaptive_state_async(
            hass, "Arbejdsdage kører vi Niveau2"
        )
        assert result == "level_2"

        mock_get_state.return_value = "boost"
        result = await _extract_adaptive_state_async(hass, "Boost mode aktiveret")
        assert result == "boost"

        mock_get_state.return_value = "eco"
        result = await _extract_adaptive_state_async(hass, "ECO kørsel")
        assert result == "eco"

        mock_get_state.return_value = "home"
        result = await _extract_adaptive_state_async(hass, "Home mode")
        assert result == "home"

        # Test cases that should be redacted (no state found)
        mock_get_state.return_value = None
        result = await _extract_adaptive_state_async(hass, "Møde med kunden")
        assert result == "**REDACTED**"

        result = await _extract_adaptive_state_async(hass, "Personlig note")
        assert result == "**REDACTED**"

        result = await _extract_adaptive_state_async(hass, "")
        assert result == "**REDACTED**"


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_diagnostics_with_intelligent_calendar_redaction(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics includes calendar data with intelligent redaction."""
    # Create a config entry
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: "10.0.0.5",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        options={},
        unique_id="SERIAL-1",
        entry_id="entry-1",
    )
    entry.add_to_hass(hass)

    # Create a mock calendar with events containing adaptive states
    mock_calendar = SimpleNamespace(
        entity_id="calendar.dantherm_calendar",
        unique_id="dantherm_calendar_entry-1",
        _storage_version=1,
        _events=[
            DanthermCalendarEvent(
                uid="event-1",
                summary="Arbejdsdage kører vi Niveau2",
                start=datetime.now(),
                end=datetime.now() + timedelta(hours=1),
                description="Privat beskrivelse der skal redactes",
                rrule="FREQ=DAILY",
                all_day=False,
            ),
            DanthermCalendarEvent(
                uid="event-2",
                summary="Weekend boost mode",
                start=date.today(),
                end=date.today() + timedelta(days=1),
                description="Mere privat info",
                all_day=True,
            ),
            DanthermCalendarEvent(
                uid="event-3",
                summary="Personlig note uden adaptive state",
                start=datetime.now(),
                end=datetime.now() + timedelta(hours=2),
                description="",
                all_day=False,
            ),
        ],
    )

    # Setup runtime data with calendar
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        ATTR_CALENDAR: mock_calendar,
    }

    # Mock the adaptive state extraction to return predictable results
    with patch(
        "config.custom_components.dantherm.diagnostics.async_get_adaptive_state_from_summary"
    ) as mock_get_state:

        def mock_state_func(hass: HomeAssistant, text: str) -> str | None:
            if "niveau2" in text.lower():
                return "level_2"
            if "boost" in text.lower():
                return "boost"
            return None

        mock_get_state.side_effect = mock_state_func

        diag = await async_get_config_entry_diagnostics(hass, entry)

        # Calendar section should be present
        assert "calendar" in diag
        assert diag["calendar"] is not None

        # Check basic calendar info
        cal_data = diag["calendar"]
        assert cal_data["entity_id"] == "calendar.dantherm_calendar"
        assert cal_data["unique_id"] == "dantherm_calendar_entry-1"
        assert cal_data["storage_version"] == 1
        assert cal_data["event_count"] == 3

        # Check statistics
        stats = cal_data["statistics"]
        assert stats["total_events"] == 3
        assert stats["recurring_events"] == 1  # 1 event has rrule
        assert stats["all_day_events"] == 1
        assert stats["events_with_description"] == 2  # 2 events have description
        assert stats["events_with_exdate"] == 0  # 0 events have exception dates

        # Check event samples with intelligent redaction
        samples = cal_data["event_samples"]
        assert len(samples) == 3

        # First event - adaptive state extracted
        sample1 = samples[0]
        assert sample1["summary_redacted"] == "level_2"
        assert sample1["description"] == "**REDACTED**"
        assert sample1["has_rrule"] is True

        # Second event - boost mode extracted
        sample2 = samples[1]
        assert sample2["summary_redacted"] == "boost"
        assert sample2["description"] == "**REDACTED**"
        assert sample2["all_day"] is True

        # Third event - no adaptive state, fully redacted
        sample3 = samples[2]
        assert sample3["summary_redacted"] == "**REDACTED**"
        assert sample3["description"] == "**REDACTED**"
