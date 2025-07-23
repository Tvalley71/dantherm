"""Test migration for Dantherm integration."""

from config.custom_components.dantherm import async_migrate_entry
from config.custom_components.dantherm.const import DOMAIN
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


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
