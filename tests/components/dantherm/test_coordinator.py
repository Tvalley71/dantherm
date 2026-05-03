"""Test the Dantherm coordinator."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import config.custom_components.dantherm.coordinator as coordinator_mod
from config.custom_components.dantherm.coordinator import DanthermCoordinator
from config.custom_components.dantherm.device_map import (
    ACTION_PENDING_MIN_READ_DELAY_MILLISECONDS,
    ATTR_ACTIONS_PENDING,
    DanthermEntityDescription,
)
import pytest

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry():
    """Return mock config entry."""
    return MockConfigEntry(
        domain="dantherm",
        title="Test Device",
        data={"host": "192.168.1.100"},
        options={},
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )


@pytest.fixture
def mock_hub():
    """Return mock hub."""
    hub = MagicMock()
    hub.async_get_data = AsyncMock(return_value={"test_data": "value"})
    return hub


async def _cancel_coordinator_tasks() -> None:
    """Cancel lingering coordinator background tasks to avoid teardown errors."""
    tasks = [
        t
        for t in asyncio.all_tasks()
        if "_process_frontend" in str(t) or "_process_backend" in str(t)
    ]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestDanthermCoordinator:
    """Test DanthermCoordinator class."""

    async def test_coordinator_initialization(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator initialization."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
            write_delay=0.3,
        )

        assert coordinator.name == "TestDeviceCoordinator"
        assert coordinator.hub is mock_hub
        assert coordinator.update_interval == timedelta(seconds=30)
        assert coordinator._config_entry is mock_config_entry

        await _cancel_coordinator_tasks()

    async def test_coordinator_update_success(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test successful data update with no entities."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # With no entities, update should return empty dict
        await coordinator.async_refresh()
        assert coordinator.data == {}

        await _cancel_coordinator_tasks()

    async def test_coordinator_update_failure(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator handles update failure gracefully."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Add a test entity to trigger update
        mock_entity = MagicMock()
        mock_entity.key = "test_sensor"
        coordinator._entities.append(mock_entity)

        # Make async_get_current_unit_mode return None to trigger failure
        mock_hub.async_get_current_unit_mode = AsyncMock(return_value=None)

        # The coordinator will now suppress UpdateFailed and just log error
        await coordinator.async_refresh()

        # Check that update was not successful
        assert not coordinator.last_update_success

        await _cancel_coordinator_tasks()

    async def test_coordinator_entity_management(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test entity add/remove management."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        mock_entity = MagicMock()
        mock_entity.key = "test_sensor"

        # Test adding entity
        await coordinator.async_add_entity(mock_entity)
        assert mock_entity in coordinator._entities

        # Initialize data dict and mock disconnect to prevent errors
        coordinator.data = {}
        mock_hub.disconnect_and_close = AsyncMock()

        # Test removing entity (will call disconnect when no entities left)
        await coordinator.async_remove_entity(mock_entity)
        assert mock_entity not in coordinator._entities

        await _cancel_coordinator_tasks()

    async def test_coordinator_write_operations(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator write operations."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
            write_delay=0.1,
        )

        mock_entity = MagicMock()
        mock_entity.key = "test_key"

        # Test entity update operation (this is what coordinator actually does)
        result = await coordinator.async_update_entity(mock_entity, {})

        # Verify the operation completed
        assert isinstance(result, dict)

        await _cancel_coordinator_tasks()

    async def test_coordinator_is_entity_installed(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test entity installation check."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Test entity not installed
        assert not coordinator.is_entity_installed("nonexistent_entity")

        # Add entity to list
        mock_entity = MagicMock()
        mock_entity.key = "test_entity"
        await coordinator.async_add_entity(mock_entity)

        # Test entity installed
        assert coordinator.is_entity_installed("test_entity")

        await _cancel_coordinator_tasks()

    async def test_pending_lifecycle_clears_only_after_delay_and_next_cycle(
        self, hass: HomeAssistant, mock_hub, mock_config_entry, monkeypatch
    ) -> None:
        """Pending action must NOT clear until BOTH the min delay has elapsed AND
        at least one subsequent update cycle has occurred after execution."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Freeze time at a known point
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        current_time = {"now": t0}

        def fake_now():
            return current_time["now"]

        # Patch the ha_now symbol used inside the coordinator module
        monkeypatch.setattr(coordinator_mod, "ha_now", fake_now)

        key = "test_action_key"

        # Set update_cycle to 5 before marking executed
        coordinator._update_cycle = 5
        coordinator._mark_pending_requested(key)
        coordinator._mark_pending_executed(key)

        executed_cycle = coordinator._pending_actions[key].executed_read_cycle
        assert executed_cycle == 5
        assert coordinator.is_entity_pending(key), "Should be pending after mark_executed"

        # --- Gate 1: same cycle, time not elapsed -> must NOT clear ---
        coordinator._process_pending_transitions()
        assert coordinator.is_entity_pending(key), (
            "Should still be pending: same update_cycle as executed_read_cycle"
        )

        # --- Gate 2: after delay, but SAME cycle -> must NOT clear ---
        current_time["now"] = t0 + timedelta(
            milliseconds=ACTION_PENDING_MIN_READ_DELAY_MILLISECONDS + 500
        )
        coordinator._process_pending_transitions()
        assert coordinator.is_entity_pending(key), (
            "Should still be pending: update_cycle has not advanced past executed_read_cycle"
        )

        # --- Gate 3: next cycle + after delay -> must clear ---
        coordinator._update_cycle = 6
        coordinator._process_pending_transitions()
        assert not coordinator.is_entity_pending(key), (
            "Pending should be cleared: delay elapsed AND update_cycle > executed_read_cycle"
        )
        assert not coordinator.has_pending_actions()

        await _cancel_coordinator_tasks()

    async def test_async_set_entity_state_triggers_actions_pending_write(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """async_set_entity_state must immediately call async_write_ha_state on the
        actions_pending binary sensor when a pending-supported entity is written."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Make enqueue_frontend return an already-resolved future so the test
        # does not block on the background processor task.
        def enqueue_frontend_immediate(coro_func, *args, **kwargs):
            fut = asyncio.get_running_loop().create_future()
            fut.set_result(None)
            return fut

        coordinator.enqueue_frontend = enqueue_frontend_immediate  # type: ignore[method-assign]

        # Build a real DanthermEntityDescription that qualifies as an "action"
        # (has data_setinternal -> _is_action_description returns True)
        action_desc = DanthermEntityDescription(
            key="test_action",
            name="Test Action",
            data_setinternal="filter_reset",
        )

        # Entity whose state will be written
        action_entity = MagicMock()
        action_entity.entity_id = "button.test_action"
        action_entity.key = "test_action"
        action_entity.entity_description = action_desc
        action_entity.extra_state_attributes = {}

        # The actions_pending binary sensor entity that should be notified
        pending_entity = MagicMock()
        pending_entity.entity_id = "binary_sensor.actions_pending"
        pending_entity.key = ATTR_ACTIONS_PENDING
        pending_entity.async_write_ha_state = MagicMock()

        coordinator._entities = [pending_entity, action_entity]

        # Register the action key as pending-supported (normally done in async_add_entity)
        coordinator._pending_supported_keys.add("test_action")

        # Initialize coordinator data cache
        coordinator.data = {}

        await coordinator.async_set_entity_state(action_entity, 1)

        # The actions_pending sensor should have been told to refresh immediately
        pending_entity.async_write_ha_state.assert_called_once()

        # And the coordinator should report a pending action in progress
        assert coordinator.has_pending_actions()
        assert coordinator.is_entity_pending("test_action")

        await _cancel_coordinator_tasks()
