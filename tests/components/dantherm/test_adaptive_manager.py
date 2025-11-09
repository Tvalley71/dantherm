"""Tests for Dantherm adaptive manager functionality."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from config.custom_components.dantherm.adaptive_manager import (
    AdaptiveEventStack,
    DanthermAdaptiveManager,
)
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util.dt import now as ha_now


class MockCalendarEvent:
    """Mock calendar event for testing."""

    def __init__(
        self,
        uid: str,
        summary: str,
        start: datetime,
        end: datetime,
        rrule: str | None = None,
    ) -> None:
        """Initialize mock calendar event."""
        self.uid = uid
        self.summary = summary
        self.start = start
        self.end = end
        self.rrule = rrule


class MockCalendar:
    """Mock calendar for testing."""

    def __init__(self, events: list[MockCalendarEvent] | None = None) -> None:
        """Initialize mock calendar."""
        self._events = events or []


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_entry.options = {}
    return mock_entry


@pytest.fixture
def adaptive_manager(hass: HomeAssistant, mock_config_entry):
    """Create an adaptive manager instance for testing."""
    return DanthermAdaptiveManager(hass, mock_config_entry)


@pytest.fixture
def event_stack():
    """Create an event stack instance for testing."""
    return AdaptiveEventStack()


class TestAdaptiveEventStack:
    """Test the AdaptiveEventStack class."""

    def test_initialization(self, event_stack):
        """Test that event stack initializes correctly."""
        assert len(event_stack) == 0
        assert event_stack._calendar is None

    def test_set_calendar(self, event_stack):
        """Test setting calendar reference."""
        mock_calendar = MockCalendar()
        event_stack.set_calendar(mock_calendar)
        assert event_stack._calendar is mock_calendar

    def test_clear_all_events(self, event_stack):
        """Test clearing all events from stack."""
        # Add some test events
        event_stack.append({"event": "test1", "event_id": "id1"})
        event_stack.append({"event": "test2", "event_id": "id2"})

        assert len(event_stack) == 2

        removed_count = event_stack.clear_all_events()

        assert len(event_stack) == 0
        assert removed_count == 2

    def test_clear_all_events_empty_stack(self, event_stack):
        """Test clearing events from empty stack."""
        removed_count = event_stack.clear_all_events()
        assert removed_count == 0


class TestAdaptiveManagerCleanup:
    """Test cleanup functionality in adaptive manager."""

    def test_cleanup_stale_events_no_calendar(self, adaptive_manager):
        """Test cleanup when no calendar is available."""
        # Add some events to the stack
        adaptive_manager.events.append({"event": "test", "event_id": "missing_id"})

        removed_count = adaptive_manager.cleanup_stale_events()

        # Should not remove events without calendar reference
        assert removed_count == 0
        assert len(adaptive_manager.events) == 1

    def test_cleanup_stale_events_with_valid_events(self, adaptive_manager):
        """Test cleanup with events that exist in calendar."""
        # Setup calendar with events
        calendar_events = [
            MockCalendarEvent(
                "valid_id", "Valid Event", ha_now(), ha_now() + timedelta(hours=1)
            )
        ]
        mock_calendar = MockCalendar(calendar_events)
        adaptive_manager._calendar = mock_calendar
        adaptive_manager.events.set_calendar(mock_calendar)

        # Add event that exists in calendar
        adaptive_manager.events.append({"event": "test", "event_id": "valid_id"})

        removed_count = adaptive_manager.cleanup_stale_events()

        # Should not remove valid events
        assert removed_count == 0
        assert len(adaptive_manager.events) == 1

    def test_cleanup_stale_events_with_invalid_events(self, adaptive_manager):
        """Test cleanup with events that don't exist in calendar."""
        # Setup calendar with one event
        calendar_events = [
            MockCalendarEvent(
                "valid_id", "Valid Event", ha_now(), ha_now() + timedelta(hours=1)
            )
        ]
        mock_calendar = MockCalendar(calendar_events)
        adaptive_manager._calendar = mock_calendar
        adaptive_manager.events.set_calendar(mock_calendar)

        # Add event that doesn't exist in calendar
        adaptive_manager.events.append({"event": "test", "event_id": "invalid_id"})

        removed_count = adaptive_manager.cleanup_stale_events()

        # Should remove invalid events
        assert removed_count == 1
        assert len(adaptive_manager.events) == 0

    def test_cleanup_stale_events_mixed_events(self, adaptive_manager):
        """Test cleanup with mix of valid and invalid events."""
        # Setup calendar with one event
        calendar_events = [
            MockCalendarEvent(
                "valid_id", "Valid Event", ha_now(), ha_now() + timedelta(hours=1)
            )
        ]
        mock_calendar = MockCalendar(calendar_events)
        adaptive_manager._calendar = mock_calendar
        adaptive_manager.events.set_calendar(mock_calendar)

        # Add mix of valid and invalid events
        adaptive_manager.events.append({"event": "valid", "event_id": "valid_id"})
        adaptive_manager.events.append({"event": "invalid", "event_id": "invalid_id"})
        adaptive_manager.events.append({"event": "no_id"})  # No event_id

        removed_count = adaptive_manager.cleanup_stale_events()

        # Should remove only the invalid event
        assert removed_count == 1
        assert len(adaptive_manager.events) == 2

    def test_cleanup_calendar_access_error(self, adaptive_manager):
        """Test cleanup when calendar access fails."""
        # Setup calendar that will cause an error
        mock_calendar = MagicMock()
        mock_calendar._events = None  # This will cause AttributeError
        adaptive_manager._calendar = mock_calendar
        adaptive_manager.events.set_calendar(mock_calendar)

        # Add event
        adaptive_manager.events.append({"event": "test", "event_id": "some_id"})

        # Should still remove events when calendar access fails (fail-safe behavior)
        removed_count = adaptive_manager.cleanup_stale_events()
        assert removed_count == 1  # Event gets removed in error case
        assert len(adaptive_manager.events) == 0


class TestCalculateEventEndTime:
    """Test end time calculation for calendar events."""

    def test_calculate_end_time_non_recurring(self, adaptive_manager):
        """Test end time calculation for non-recurring events."""
        start_time = ha_now()
        end_time = start_time + timedelta(hours=2)

        event = MockCalendarEvent("test_id", "Test Event", start_time, end_time)

        calculated_end = adaptive_manager._calculate_event_end_time(event)

        # For non-recurring events, should return the original end time
        assert calculated_end == end_time

    def test_calculate_end_time_recurring(self, adaptive_manager):
        """Test end time calculation for recurring events."""
        start_time = ha_now()
        # Create a reasonable duration - 2 hours
        original_end = start_time + timedelta(hours=2)

        event = MockCalendarEvent(
            "test_id", "Test Event", start_time, original_end, rrule="FREQ=DAILY"
        )

        calculated_end = adaptive_manager._calculate_event_end_time(event)

        # For recurring events with reasonable duration, should return original calculation
        expected_duration = original_end - start_time
        expected_end = start_time + expected_duration
        assert calculated_end == expected_end

    def test_calculate_end_time_recurring_suspicious_duration(self, adaptive_manager):
        """Test end time calculation for recurring events with suspicious long duration."""
        start_time = ha_now()
        # Create an end time that's more than a year in the future
        original_end = start_time + timedelta(days=400)

        event = MockCalendarEvent(
            "test_id", "Test Event", start_time, original_end, rrule="FREQ=DAILY"
        )

        with patch(
            "config.custom_components.dantherm.adaptive_manager._LOGGER"
        ) as mock_logger:
            calculated_end = adaptive_manager._calculate_event_end_time(event)

            # Should limit to 24 hours maximum
            expected_end = start_time + timedelta(hours=24)
            assert calculated_end == expected_end

            # Should log a warning
            mock_logger.warning.assert_called_once()


class TestEventStackIntegration:
    """Test integration between event stack and cleanup."""

    async def test_startup_cleanup_called(self, adaptive_manager):
        """Test that cleanup is called during setup."""
        # Create mock attributes the setup method needs
        with (
            patch.object(
                adaptive_manager,
                "get_device_id",
                return_value="device_123",
                create=True,
            ),
            patch.object(adaptive_manager, "_adaptive_triggers", {}),
            patch.object(
                adaptive_manager, "cleanup_stale_events", return_value=2
            ) as mock_cleanup,
        ):
            await adaptive_manager.async_set_up_adaptive_manager()
            mock_cleanup.assert_called_once()
