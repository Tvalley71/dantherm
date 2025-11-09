"""Extra discovery fallback tests for Dantherm discovery."""

from __future__ import annotations

from config.custom_components.dantherm.discovery import async_discover
import pytest

from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_async_discover_unicast_fallback_local(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When broadcast finds nothing, fall back to unicast sweep on local subnet."""

    # Local IPs as detected by HA
    async def fake_get_local_ips(hass: HomeAssistant) -> list[str]:
        return ["192.168.50.10"]

    async def fake_discover_broadcast(
        hass: HomeAssistant,
        bcast_ip: str,
        probe: bytes,
        local_ips: list[str] | None,
    ):
        # No device found via broadcast on local subnet
        return []

    async def fake_discover_unicast_sweep(
        hass: HomeAssistant, base_ip: str, probe: bytes
    ):
        # Return a device when sweeping the local subnet
        if base_ip.startswith("192.168.50."):
            return [{"ip": "192.168.50.42", "name": "UnicastDevice"}]
        return []

    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._async_get_local_ips",
        fake_get_local_ips,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_broadcast",
        fake_discover_broadcast,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_unicast_sweep",
        fake_discover_unicast_sweep,
    )

    result = await async_discover(hass)
    assert result == [{"ip": "192.168.50.42", "name": "UnicastDevice"}]


@pytest.mark.asyncio
async def test_async_discover_global_broadcast_last_resort(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When local broadcast and unicast find nothing, try global broadcast."""

    async def fake_get_local_ips(hass: HomeAssistant) -> list[str]:
        return ["10.10.10.2"]

    async def fake_discover_broadcast(
        hass: HomeAssistant,
        bcast_ip: str,
        probe: bytes,
        local_ips: list[str] | None,
    ):
        # Only return a device for the global broadcast address
        if bcast_ip == "255.255.255.255":
            return [{"ip": "10.10.10.99", "name": "GlobalDevice"}]
        return []

    async def fake_discover_unicast_sweep(
        hass: HomeAssistant, base_ip: str, probe: bytes
    ):
        return []

    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._async_get_local_ips",
        fake_get_local_ips,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_broadcast",
        fake_discover_broadcast,
    )
    monkeypatch.setattr(
        "config.custom_components.dantherm.discovery._discover_unicast_sweep",
        fake_discover_unicast_sweep,
    )

    result = await async_discover(hass)
    assert result == [{"ip": "10.10.10.99", "name": "GlobalDevice"}]
