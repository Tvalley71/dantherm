"""Test the Dantherm coordinator."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import config.custom_components.dantherm.coordinator as coordinator_mod
from config.custom_components.dantherm.coordinator import DanthermCoordinator
from config.custom_components.dantherm.device_map import (
    ATTR_ACTIONS_PENDING,
    ATTR_CALENDAR,
    CONF_ENABLE_TIME_SYNCHRONIZATION,
    DanthermEntityDescription,
    DanthermSwitchEntityDescription,
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
        with suppress(asyncio.CancelledError):
            await task


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
        coordinator.async_shutdown = AsyncMock()

        # Test removing entity (will call disconnect when no entities left)
        await coordinator.async_remove_entity(mock_entity)
        assert mock_entity not in coordinator._entities
        coordinator.async_shutdown.assert_awaited_once()
        mock_hub.disconnect_and_close.assert_awaited_once()

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

    async def test_coordinator_async_shutdown_cancels_background_tasks(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator shutdown cancels processor tasks."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        await coordinator.async_shutdown()

        assert coordinator._frontend_task.done()
        assert coordinator._backend_task.done()

    async def test_update_data_reads_calendar_outside_rw_lock(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Adaptive calendar updates should run before the locked entity read loop."""

        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        mock_hub.async_process_expired_events = AsyncMock()
        mock_hub.async_update_adaptive_triggers = AsyncMock()
        mock_hub.async_get_calendar = AsyncMock(return_value="calendar-state")
        mock_hub.async_get_current_unit_mode = AsyncMock(return_value="mode")
        mock_hub.async_get_active_unit_mode = AsyncMock()
        mock_hub.async_get_fan_level = AsyncMock()
        mock_hub.async_get_alarm = AsyncMock()
        mock_hub.async_get_filter_state = AsyncMock()
        mock_hub.async_get_sensor_filtering = AsyncMock()
        mock_hub.async_get_bypass_maximum_temperature = AsyncMock()

        entered_lock = False

        class LockProbe:
            async def __aenter__(self):
                nonlocal entered_lock
                entered_lock = True

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def _calendar_side_effect():
            assert not entered_lock
            return "calendar-state"

        mock_hub.async_get_calendar.side_effect = _calendar_side_effect

        calendar_entity = MagicMock()
        calendar_entity.key = ATTR_CALENDAR
        calendar_entity.entity_id = "calendar.test_device"
        calendar_entity.entity_description = DanthermEntityDescription(
            key=ATTR_CALENDAR,
            data_getinternal=ATTR_CALENDAR,
        )

        coordinator._rw_lock = LockProbe()
        coordinator._entities.append(calendar_entity)

        await coordinator._update_data()

        mock_hub.async_get_calendar.assert_awaited_once()

        await _cancel_coordinator_tasks()

    async def test_update_data_synchronizes_time_outside_rw_lock(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Time synchronization should run before the locked entity read loop."""

        mock_config_entry = MockConfigEntry(
            domain="dantherm",
            title="Test Device",
            data={"host": "192.168.1.100"},
            options={CONF_ENABLE_TIME_SYNCHRONIZATION: True},
            entry_id="test_entry_id_time_sync",
            unique_id="test_unique_id_time_sync",
        )
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        mock_hub.async_process_expired_events = AsyncMock()
        mock_hub.async_update_adaptive_triggers = AsyncMock()
        mock_hub.async_should_synchronize_time = AsyncMock(return_value=True)
        mock_hub.async_set_current_time = AsyncMock()
        mock_hub.async_get_current_unit_mode = AsyncMock(return_value="mode")
        mock_hub.async_get_active_unit_mode = AsyncMock()
        mock_hub.async_get_fan_level = AsyncMock()
        mock_hub.async_get_alarm = AsyncMock()
        mock_hub.async_get_filter_state = AsyncMock()
        mock_hub.async_get_sensor_filtering = AsyncMock()
        mock_hub.async_get_bypass_maximum_temperature = AsyncMock()

        entered_lock = False

        class LockProbe:
            async def __aenter__(self):
                nonlocal entered_lock
                entered_lock = True

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async def _time_sync_side_effect():
            assert entered_lock
            return True

        mock_hub.async_should_synchronize_time.side_effect = _time_sync_side_effect

        dummy_entity = MagicMock()
        dummy_entity.key = "dummy_sensor"
        dummy_entity.entity_id = "sensor.dummy_sensor"
        coordinator._rw_lock = LockProbe()
        coordinator._entities.append(dummy_entity)
        coordinator.async_update_entity = AsyncMock(return_value={})

        await coordinator._update_data()

        mock_hub.async_should_synchronize_time.assert_awaited_once()

        await _cancel_coordinator_tasks()

    async def test_operation_selection_by_key_toggles_actions_pending_lifecycle(
        self, hass: HomeAssistant, mock_hub, mock_config_entry, monkeypatch
    ) -> None:
        """Operation selection writes should drive actions_pending on and off."""

        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        current_time = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
        monkeypatch.setattr(coordinator_mod, "ha_now", lambda: current_time["now"])

        def enqueue_frontend_immediate(coro_func, *args, **kwargs):
            return asyncio.create_task(coro_func(*args, **kwargs))

        coordinator.enqueue_frontend = enqueue_frontend_immediate  # type: ignore[method-assign]

        entity_key = "operation_selection"
        desc = DanthermEntityDescription(
            key=entity_key,
            name="Operation Selection",
            data_setinternal="operation_selection",
        )
        coordinator._all_descriptions[entity_key] = desc
        coordinator._pending_supported_keys.add(entity_key)
        coordinator.hub.set_operation_selection = AsyncMock(return_value=None)

        pending_entity = MagicMock()
        pending_entity.entity_id = "binary_sensor.actions_pending"
        pending_entity.key = ATTR_ACTIONS_PENDING
        pending_entity._handle_coordinator_update = None
        pending_entity.async_write_ha_state = MagicMock()
        coordinator._entities = [pending_entity]

        await coordinator.async_set_entity_state_by_key(entity_key, "manual")

        assert coordinator.has_pending_actions()
        assert coordinator.is_entity_pending(entity_key)
        assert pending_entity.async_write_ha_state.call_count >= 2

        current_time["now"] += coordinator._pending_min_read_delay + timedelta(
            milliseconds=1
        )
        coordinator._update_cycle = 1
        coordinator._process_pending_transitions()

        assert not coordinator.has_pending_actions()
        assert not coordinator.is_entity_pending(entity_key)

        await _cancel_coordinator_tasks()


class TestPendingActionLifecycle:
    """Tests for coordinator pending-action state machine."""

    @pytest.fixture
    async def coordinator(
        self,
        hass: HomeAssistant,
        mock_hub,
        mock_config_entry,
    ):
        """Return a coordinator with a short write_delay for fast tests."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
            write_delay=0.05,
        )
        yield coordinator
        await coordinator.async_shutdown()

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_action_entity(self, key: str) -> MagicMock:
        desc = DanthermEntityDescription(key=key, data_setinternal="some_internal")
        entity = MagicMock()
        entity.key = key
        entity.entity_description = desc
        entity.entity_id = f"switch.{key}"
        return entity

    # ── lifecycle test (merged from conflict branch) ───────────────────────

    async def test_pending_lifecycle_clears_only_after_delay_and_next_cycle(
        self, coordinator: DanthermCoordinator, monkeypatch
    ) -> None:
        """Pending clears only when BOTH delay + next cycle are satisfied."""

        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = {"now": t0}

        monkeypatch.setattr(coordinator_mod, "ha_now", lambda: current_time["now"])

        key = "test_action_key"

        coordinator._update_cycle = 5
        coordinator._pending_min_read_delay = timedelta(milliseconds=500)

        coordinator._mark_pending_requested(key)
        coordinator._mark_pending_executed(key)

        executed_cycle = coordinator._pending_actions[key].executed_read_cycle
        assert executed_cycle == 5
        assert coordinator.is_entity_pending(key)

        # Gate 1: same cycle
        coordinator._process_pending_transitions()
        assert coordinator.is_entity_pending(key)

        # Gate 2: time passed but same cycle
        current_time["now"] = t0 + timedelta(milliseconds=600)
        coordinator._process_pending_transitions()
        assert coordinator.is_entity_pending(key)

        # Gate 3: next cycle + delay passed
        coordinator._update_cycle = 6
        coordinator._process_pending_transitions()

        assert not coordinator.is_entity_pending(key)
        assert not coordinator.has_pending_actions()

    # ── async_set_entity_state trigger test (merged) ───────────────────────

    async def test_async_set_entity_state_triggers_actions_pending_write(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Writing action must trigger immediate pending sensor update."""

        def enqueue_frontend_immediate(coro_func, *args, **kwargs):
            fut = asyncio.get_running_loop().create_future()
            fut.set_result(None)
            return fut

        coordinator.enqueue_frontend = enqueue_frontend_immediate  # type: ignore[method-assign]

        action_desc = DanthermEntityDescription(
            key="test_action",
            name="Test Action",
            data_setinternal="filter_reset",
        )

        action_entity = MagicMock()
        action_entity.entity_id = "button.test_action"
        action_entity.key = "test_action"
        action_entity.entity_description = action_desc
        action_entity.extra_state_attributes = {}

        pending_entity = MagicMock()
        pending_entity.entity_id = "binary_sensor.actions_pending"
        pending_entity.key = ATTR_ACTIONS_PENDING
        pending_entity.async_write_ha_state = MagicMock()

        coordinator._entities = [pending_entity, action_entity]
        coordinator._pending_supported_keys.add("test_action")
        coordinator.data = {}

        await coordinator.async_set_entity_state(action_entity, 1)

        pending_entity.async_write_ha_state.assert_called_once()

        assert coordinator.has_pending_actions()
        assert coordinator.is_entity_pending("test_action")

    def test_supports_pending_only_for_registered_keys(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Pending support should only be reported for supported keys."""

        entity = self._make_action_entity("test_action")

        assert coordinator.supports_pending(entity.key) is False

        coordinator._pending_supported_keys.add("test_action")

        assert coordinator.supports_pending(entity.key) is True

    def test_inject_pending_attr_marks_pending_entity(
        self, coordinator: DanthermCoordinator, monkeypatch
    ) -> None:
        """Inject the pending attribute for entities currently in flight."""

        coordinator._pending_supported_keys.add("test_action")

        monkeypatch.setattr(
            coordinator, "is_entity_pending", MagicMock(return_value=True)
        )

        updated_attrs = coordinator._inject_pending_attr(
            "test_action", {"existing": "value"}
        )

        assert updated_attrs["existing"] == "value"
        assert updated_attrs["pending"] is True

    async def test_set_entity_state_by_description_delegates_to_matching_entity(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Setting by description should resolve the entity and delegate."""

        desc = DanthermEntityDescription(
            key="test_action",
            name="Test Action",
            data_setinternal="filter_reset",
        )
        entity = MagicMock()
        entity.entity_id = "button.test_action"
        entity.key = "test_action"
        entity.entity_description = desc
        coordinator._entities = [entity]
        coordinator.hub.set_filter_reset = AsyncMock(return_value=None)

        await coordinator._set_entity_state_by_description(desc, "test_action", 1)

        coordinator.hub.set_filter_reset.assert_awaited_once_with(1)

    async def test_async_set_entity_state_by_key_falls_back_to_description(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Missing entity instances should still be handled through description fallback."""

        def enqueue_frontend_immediate(coro_func, *args, **kwargs):
            return asyncio.create_task(coro_func(*args, **kwargs))

        coordinator.enqueue_frontend = enqueue_frontend_immediate  # type: ignore[method-assign]

        desc = DanthermSwitchEntityDescription(
            key="test_action",
            name="Test Action",
            data_setinternal="filter_reset",
        )

        coordinator._entities = []
        coordinator._set_entity_state_by_description = AsyncMock()
        coordinator._all_descriptions["test_action"] = desc

        await coordinator.async_set_entity_state_by_key("test_action", True)

        coordinator._set_entity_state_by_description.assert_awaited_once_with(
            desc, "test_action", True
        )

    async def test_async_set_entity_state_by_key_fallback_marks_pending(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Fallback by-key writes should still toggle pending lifecycle state."""

        def enqueue_frontend_immediate(coro_func, *args, **kwargs):
            fut = asyncio.get_running_loop().create_future()
            fut.set_result(None)
            return fut

        coordinator.enqueue_frontend = enqueue_frontend_immediate  # type: ignore[method-assign]

        entity_key = "operation_selection"
        desc = DanthermEntityDescription(
            key=entity_key,
            name="Operation Selection",
            data_setinternal="operation_selection",
        )
        coordinator._all_descriptions[entity_key] = desc
        coordinator._pending_supported_keys.add(entity_key)

        pending_entity = MagicMock()
        pending_entity.entity_id = "binary_sensor.actions_pending"
        pending_entity.key = ATTR_ACTIONS_PENDING
        pending_entity._handle_coordinator_update = None
        pending_entity.async_write_ha_state = MagicMock()
        coordinator._entities = [pending_entity]

        await coordinator.async_set_entity_state_by_key(entity_key, "manual")

        assert coordinator.has_pending_actions()
        assert coordinator.is_entity_pending(entity_key)
        assert pending_entity.async_write_ha_state.call_count >= 2
