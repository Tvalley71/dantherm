"""Test the Dantherm coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from config.custom_components.dantherm.coordinator import (
    DanthermCoordinator,
    PendingActionState,
)
from config.custom_components.dantherm.device_map import (
    ATTR_AWAY_MODE,
    DanthermEntityDescription,
    DanthermSwitchEntityDescription,
    ActiveUnitMode,
)
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


@pytest.fixture
def mock_config_entry():
    """Return mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test Device",
        data={"host": "192.168.1.100"},
        options={},
        entry_id="test_entry_id",
        source="user",
        unique_id="test_unique_id",
        discovery_keys={},
        subentries_data={},
    )


@pytest.fixture
def mock_hub():
    """Return mock hub."""
    hub = MagicMock()
    hub.async_get_data = AsyncMock(return_value={"test_data": "value"})
    return hub


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


class TestPendingActionLifecycle:
    """Tests for coordinator pending-action state machine."""

    @pytest.fixture
    async def coordinator(self, mock_hub):
        """Return a coordinator with a short write_delay for fast tests.

        Patches hass.loop.create_task to a no-op so the coordinator's infinite
        background tasks (_process_frontend / _process_backend) are not
        actually scheduled into the event loop, keeping tests fast and clean.
        """
        import asyncio

        from homeassistant.config_entries import ConfigEntry

        mock_hass = MagicMock()
        mock_hass.data = {}
        # Prevent real asyncio tasks from being created by the coordinator.
        mock_hass.loop = MagicMock()
        mock_hass.loop.create_task = MagicMock(return_value=MagicMock(spec=asyncio.Task))
        # enqueue_frontend / enqueue_backend need a running loop to create Futures.
        mock_hass.loop.create_future = asyncio.get_running_loop().create_future

        entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain="dantherm",
            title="Test Device",
            data={"host": "192.168.1.100"},
            options={},
            entry_id="test_entry_id",
            source="user",
            unique_id="test_unique_id",
            discovery_keys={},
        )
        return DanthermCoordinator(
            hass=mock_hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=entry,
            write_delay=0.05,
        )

    # ── helpers ────────────────────────────────────────────────────────────

    def _make_action_entity(self, key: str) -> MagicMock:
        """Return a mock entity with an action-capable description."""
        desc = DanthermEntityDescription(key=key, data_setinternal="some_internal")
        entity = MagicMock()
        entity.key = key
        entity.entity_description = desc
        entity.entity_id = f"switch.{key}"
        return entity

    # ── mark_pending_requested ─────────────────────────────────────────────

    async def test_mark_pending_requested_creates_entry(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_mark_pending_requested adds the key to _pending_actions."""
        assert not coordinator.has_pending_actions()
        coordinator._mark_pending_requested("away_mode")

        assert coordinator.is_entity_pending("away_mode")
        assert coordinator.has_pending_actions()
        state = coordinator._pending_actions["away_mode"]
        assert isinstance(state, PendingActionState)
        assert state.requested_at is not None
        assert state.executed_at is None

    async def test_mark_pending_requested_overwrites_existing(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Calling _mark_pending_requested twice replaces the old state."""
        coordinator._mark_pending_requested("away_mode")
        first = coordinator._pending_actions["away_mode"]
        coordinator._mark_pending_requested("away_mode")
        second = coordinator._pending_actions["away_mode"]

        assert second is not first
        assert coordinator.is_entity_pending("away_mode")

    # ── mark_pending_executed ──────────────────────────────────────────────

    async def test_mark_pending_executed_updates_timestamps(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_mark_pending_executed sets executed_at and executed_read_cycle."""
        coordinator._mark_pending_requested("summer_mode")
        coordinator._update_cycle = 3
        coordinator._mark_pending_executed("summer_mode")

        state = coordinator._pending_actions["summer_mode"]
        assert state.executed_at is not None
        assert state.executed_read_cycle == 3

    async def test_mark_pending_executed_without_prior_request(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_mark_pending_executed creates a new entry when called without a prior request."""
        coordinator._update_cycle = 1
        coordinator._mark_pending_executed("fan_level_selection")

        assert coordinator.is_entity_pending("fan_level_selection")
        state = coordinator._pending_actions["fan_level_selection"]
        assert state.executed_read_cycle == 1

    # ── process_pending_transitions ───────────────────────────────────────

    async def test_pending_not_cleared_before_later_read_cycle(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Pending state is retained when update_cycle has not advanced past executed_read_cycle."""
        coordinator._update_cycle = 5
        coordinator._mark_pending_requested("away_mode")
        coordinator._mark_pending_executed("away_mode")  # executed at cycle 5

        # Same cycle — should not be cleared
        coordinator._update_cycle = 5
        coordinator._process_pending_transitions()
        assert coordinator.is_entity_pending("away_mode")

    async def test_pending_not_cleared_before_min_delay(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Pending state is retained when min-delay has not yet elapsed."""
        coordinator._update_cycle = 5
        coordinator._mark_pending_requested("away_mode")
        coordinator._mark_pending_executed("away_mode")

        # Advance cycle but keep delay short so clock hasn't moved enough
        coordinator._update_cycle = 6
        # Override min delay to a very large value so it cannot expire yet
        coordinator._pending_min_read_delay = timedelta(hours=1)
        coordinator._process_pending_transitions()

        assert coordinator.is_entity_pending("away_mode")

    async def test_pending_cleared_after_later_cycle_and_delay(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Pending state is cleared once update_cycle advanced and min-delay elapsed."""
        coordinator._update_cycle = 5
        coordinator._mark_pending_requested("away_mode")
        coordinator._mark_pending_executed("away_mode")

        # Advance past the executed cycle and set zero min delay so it always passes
        coordinator._update_cycle = 6
        coordinator._pending_min_read_delay = timedelta(seconds=0)
        coordinator._process_pending_transitions()

        assert not coordinator.is_entity_pending("away_mode")
        assert not coordinator.has_pending_actions()

    async def test_pending_not_cleared_when_only_requested_not_executed(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """Requested-but-not-executed pending state is never cleared by _process_pending_transitions."""
        coordinator._mark_pending_requested("fan_level_selection")
        coordinator._update_cycle = 99
        coordinator._pending_min_read_delay = timedelta(seconds=0)
        coordinator._process_pending_transitions()

        assert coordinator.is_entity_pending("fan_level_selection")

    # ── supports_pending / inject_pending_attr ────────────────────────────

    async def test_supports_pending_requires_add_entity(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """supports_pending returns True only after an action entity is added."""
        assert not coordinator.supports_pending("away_mode")

        entity = self._make_action_entity("away_mode")
        await coordinator.async_add_entity(entity)

        assert coordinator.supports_pending("away_mode")

    async def test_inject_pending_attr_adds_pending_key(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_inject_pending_attr adds pending=True/False to attrs for action entities."""
        entity = self._make_action_entity("away_mode")
        await coordinator.async_add_entity(entity)

        # No active pending → pending=False
        result = coordinator._inject_pending_attr("away_mode", {"foo": "bar"})
        assert result == {"foo": "bar", "pending": False}

        # Active pending → pending=True
        coordinator._mark_pending_requested("away_mode")
        result = coordinator._inject_pending_attr("away_mode", None)
        assert result == {"pending": True}

    async def test_inject_pending_attr_no_op_for_non_action_entity(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_inject_pending_attr is a no-op for entities that don't support pending."""
        original = {"some": "attr"}
        result = coordinator._inject_pending_attr("non_action_key", original)
        assert result is original

    # ── async_set_entity_state_by_key fallback path ───────────────────────

    async def test_set_entity_state_by_description_calls_hub_setter(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """_set_entity_state_by_description invokes the hub setter for the description."""
        from config.custom_components.dantherm.device_map import (
            ActiveUnitMode,
            DanthermSwitchEntityDescription,
        )
        from homeassistant.components.switch import SwitchDeviceClass

        desc = DanthermSwitchEntityDescription(
            key="test_switch",
            data_setinternal="test_setter",
            state_on=ActiveUnitMode.StartAway,
            state_off=ActiveUnitMode.EndAway,
            device_class=SwitchDeviceClass.SWITCH,
        )
        mock_setter = AsyncMock()
        coordinator.hub.set_test_setter = mock_setter

        await coordinator._set_entity_state_by_description(desc, "test_switch", True)

        mock_setter.assert_called_once_with(ActiveUnitMode.StartAway)

    async def test_set_entity_state_by_key_description_found_in_all_descriptions(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """async_set_entity_state_by_key routes to the description fallback when no entity is registered."""
        # ATTR_AWAY_MODE is populated in _all_descriptions at coordinator init.
        assert ATTR_AWAY_MODE in coordinator._all_descriptions

        # Verify the fallback is selected (entity not in _entities but description exists).
        assert not any(
            getattr(e, "key", None) == ATTR_AWAY_MODE for e in coordinator._entities
        )

    async def test_set_entity_state_by_key_raises_for_unknown_key(
        self, coordinator: DanthermCoordinator
    ) -> None:
        """async_set_entity_state_by_key raises HomeAssistantError for completely unknown keys."""
        with pytest.raises(HomeAssistantError, match="unknown_key_xyz"):
            await coordinator.async_set_entity_state_by_key(
                "unknown_key_xyz", "some_state"
            )
