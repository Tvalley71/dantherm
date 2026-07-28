"""Test migration for Dantherm integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from config.custom_components.dantherm import (
    _migrate_sensor_filtering_option,
    async_migrate_entry,
    async_setup_entry,
)
from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.device_map import (
    ATTR_SENSOR_FILTERING,
    CONF_ENABLE_SENSOR_FILTERING,
)
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_migrate_entry(hass: HomeAssistant) -> None:
    """Test migration from disable_alarm_notifications to disable_notifications."""

    # Simulate an old config entry
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test",
        data={},
        options={"disable_alarm_notifications": True},
        entry_id="test123",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    # Add the entry to Home Assistant's config entries
    await hass.config_entries.async_add(entry)

    # Run migration
    migrated = await async_migrate_entry(hass, entry)
    assert migrated
    assert "disable_alarm_notifications" not in entry.options
    assert "disable_notifications" in entry.options
    assert entry.options["disable_notifications"] is True


@pytest.mark.asyncio
async def test_migrate_sensor_filtering_option_from_store(hass: HomeAssistant) -> None:
    """Migrate sensor filtering from legacy Dantherm store when switch state is unavailable."""
    await Store(hass, 1, "Dantherm_entities").async_save(
        {"entities": {ATTR_SENSOR_FILTERING: True}}
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Dantherm",
        data={CONF_NAME: "Dantherm"},
        options={},
        entry_id="entry_sensor_filtering_store",
    )

    options, changed = await _migrate_sensor_filtering_option(hass, entry, {})

    assert changed is True
    assert options[CONF_ENABLE_SENSOR_FILTERING] is True


@pytest.mark.asyncio
async def test_migrate_sensor_filtering_option_self_heals_false(
    hass: HomeAssistant,
) -> None:
    """Fix previously missed migration when option is false but legacy store says true."""
    await Store(hass, 1, "Dantherm_entities").async_save(
        {"entities": {ATTR_SENSOR_FILTERING: True}}
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Dantherm",
        data={CONF_NAME: "Dantherm"},
        options={CONF_ENABLE_SENSOR_FILTERING: False},
        entry_id="entry_sensor_filtering_heal",
    )

    options = {CONF_ENABLE_SENSOR_FILTERING: False}
    updated_options, changed = await _migrate_sensor_filtering_option(
        hass, entry, options
    )

    assert changed is True
    assert updated_options[CONF_ENABLE_SENSOR_FILTERING] is True


@pytest.mark.asyncio
async def test_migrate_entry_v3_to_v4_sensor_filtering_from_store(
    hass: HomeAssistant,
) -> None:
    """Migrate v3 entry to v4 and transfer sensor filtering from legacy store."""
    await Store(hass, 1, "Dantherm_entities").async_save(
        {"entities": {ATTR_SENSOR_FILTERING: True}}
    )

    entry = ConfigEntry(
        version=3,
        minor_version=1,
        domain=DOMAIN,
        title="Dantherm",
        data={CONF_NAME: "Dantherm"},
        options={},
        entry_id="entry_v3_to_v4_sensor_filtering",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    await hass.config_entries.async_add(entry)

    migrated = await async_migrate_entry(hass, entry)

    assert migrated is True
    assert entry.version == 4
    assert entry.options[CONF_ENABLE_SENSOR_FILTERING] is True


@pytest.mark.asyncio
async def test_migrate_entry_v3_to_v4_sensor_filtering_unknown_store_value_defaults_false(
    hass: HomeAssistant,
) -> None:
    """Migrate v3 entry to v4 and default to false for unknown legacy payload type."""
    await Store(hass, 1, "Dantherm_entities").async_save(
        {"entities": {ATTR_SENSOR_FILTERING: {"unexpected": "value"}}}
    )

    entry = ConfigEntry(
        version=3,
        minor_version=1,
        domain=DOMAIN,
        title="Dantherm",
        data={CONF_NAME: "Dantherm"},
        options={},
        entry_id="entry_v3_to_v4_sensor_filtering_unknown",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    await hass.config_entries.async_add(entry)

    migrated = await async_migrate_entry(hass, entry)

    assert migrated is True
    assert entry.version == 4
    assert entry.options[CONF_ENABLE_SENSOR_FILTERING] is False


@pytest.mark.asyncio
async def test_setup_entry_does_not_reapply_legacy_sensor_filtering_migration(
    hass: HomeAssistant,
) -> None:
    """Setup should not re-apply the legacy sensor-filtering migration on every startup."""
    await Store(hass, 1, "Dantherm_entities").async_save(
        {"entities": {ATTR_SENSOR_FILTERING: True}}
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Dantherm",
        data={
            CONF_NAME: "Dantherm",
            "host": "127.0.0.1",
            "port": 502,
            "scan_interval": 5,
        },
        options={},
        entry_id="entry_sensor_filtering_setup",
    )

    with (
        patch("config.custom_components.dantherm.DanthermDevice") as mock_device_cls,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        mock_device = mock_device_cls.return_value
        mock_device.async_init_and_connect = AsyncMock(return_value=MagicMock())
        mock_device.async_start = AsyncMock()
        mock_device.async_init_after_start = AsyncMock()
        mock_device.disconnect_and_close = AsyncMock()

        result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.options == {}
