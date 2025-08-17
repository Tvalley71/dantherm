"""Test discovery for Dantherm integration."""

from config.custom_components.dantherm import discovery
from config.custom_components.dantherm.discovery import (
    _get_broadcast,
    _get_subnet,
    async_discover,
)
import pytest

from homeassistant.core import HomeAssistant


@pytest.mark.parametrize(
    ("ip", "expected"),
    [
        ("192.168.1.42", "192.168.1.255"),
        ("10.0.0.5", "10.0.0.255"),
        ("172.16.0.100", "172.16.0.255"),
        ("invalid", ""),
        ("", ""),
        ("192.168.1", ""),
    ],
)
def test_get_broadcast(ip: str, expected: str) -> None:
    """Test _get_broadcast returns correct /24 broadcast address or empty string."""
    assert _get_broadcast(ip) == expected


@pytest.mark.parametrize(
    ("ip", "expected"),
    [
        ("192.168.1.42", "192.168.1"),
        ("10.0.0.5", "10.0.0"),
        ("172.16.0.100", "172.16.0"),
        ("invalid", ""),
        ("", ""),
        ("192.168.1", ""),
    ],
)
def test_get_subnet(ip: str, expected: str) -> None:
    """Test _get_subnet returns correct /24 subnet or empty string."""
    assert _get_subnet(ip) == expected


@pytest.mark.asyncio
async def test_async_discover_returns_empty_list(hass: HomeAssistant) -> None:
    """Test async_discover returns empty list if no devices found."""
    # Patch _discover_broadcast and _discover_unicast_sweep to return empty

    async def fake_discover_broadcast(*args, **kwargs):
        return []

    async def fake_discover_unicast_sweep(*args, **kwargs):
        return []

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(discovery, "_discover_broadcast", fake_discover_broadcast)
    monkeypatch.setattr(
        discovery, "_discover_unicast_sweep", fake_discover_unicast_sweep
    )

    # Mock hass.config.api.local_ip
    hass.config.api = type("api", (), {})()
    hass.config.api.local_ip = "192.168.1.2"

    result = await async_discover(hass)
    assert result == []


@pytest.mark.asyncio
async def test_async_discover_with_last_known_ip(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test async_discover uses last_known_ip if nothing found on current subnet."""
    # Arrange
    hass.config.api = type("api", (), {})()
    hass.config.api.local_ip = "192.168.1.2"

    called = {}

    async def fake_discover_broadcast(hass: HomeAssistant, bcast_ip: str, probe: bool):
        called.setdefault("broadcasts", []).append(bcast_ip)
        # Only return device if broadcast is on last_known_ip subnet
        if bcast_ip == "10.0.0.255":
            return [{"ip": "10.0.0.42", "name": "TestDevice"}]
        return []

    async def fake_discover_unicast_sweep(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_broadcast",
        fake_discover_broadcast,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_unicast_sweep",
        fake_discover_unicast_sweep,
    )

    # Act
    result = await async_discover(hass, last_known_ip="10.0.0.5")

    # Assert
    assert result == [{"ip": "10.0.0.42", "name": "TestDevice"}]
    assert "10.0.0.255" in called["broadcasts"]


@pytest.mark.asyncio
async def test_async_discover_with_broadcast_ip(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test async_discover uses provided broadcast_ip."""
    hass.config.api = type("api", (), {})()
    hass.config.api.local_ip = "192.168.1.2"

    async def fake_discover_broadcast(hass: HomeAssistant, bcast_ip: str, probe: bool):
        if bcast_ip == "172.16.0.255":
            return [{"ip": "172.16.0.42", "name": "BroadcastDevice"}]
        return []

    async def fake_discover_unicast_sweep(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_broadcast",
        fake_discover_broadcast,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_unicast_sweep",
        fake_discover_unicast_sweep,
    )

    result = await async_discover(hass, broadcast_ip="172.16.0.255")
    assert result == [{"ip": "172.16.0.42", "name": "BroadcastDevice"}]
