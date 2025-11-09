"""Dantherm discovery implementation."""

# Dantherm / Pluggit discovery helper for Home Assistant
# - Sends a UDP broadcast on port 6400 with a known UUID probe

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

from homeassistant.components import network
from homeassistant.core import HomeAssistant

# Default broadcast address if not specified
DISCOVERY_BROADCAST_DEFAULT = "255.255.255.255"
# UDP port used by devices for discovery
DISCOVERY_PORT = 6400
# Number of times to resend the probe
DISCOVERY_RETRIES = 6
# Delay between retries (seconds)
DISCOVERY_INTERVAL = 0.4
# Time to wait for responses after sending probes (seconds)
DISCOVERY_LISTEN_TIMEOUT = 5.0

# UUID payload used to probe devices
PROBE_UUID = b"b26dd68e-3335-11e3-bfea-3c970e317c6d"


_LOGGER = logging.getLogger(__name__)


def _get_broadcast(ip: str) -> str:
    """Return the /24 broadcast address for an IPv4 address, or None if invalid."""
    parts = ip.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return f"{parts[0]}.{parts[1]}.{parts[2]}.255"
    return ""


def _get_subnet(ip: str) -> str:
    """Return the /24 subnet for an IPv4 address as a string, or None if invalid."""
    parts = ip.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    return ""


def _parse_name_from_reply(data: bytes) -> str | None:
    """Parse the device name from a UDP reply.

    Replies start with the ASCII name (null-terminated).
    """
    if not data:
        return None
    end = data.find(b"\x00")
    if end == -1:
        end = min(len(data), 32)
    try:
        name = data[:end].decode("ascii", errors="ignore").strip()
        if name:
            return name
    except UnicodeDecodeError:
        pass
    return None


async def _async_get_local_ips(hass: HomeAssistant) -> list[str]:
    """Return all IPv4 addresses for Home Assistant host."""
    adapters = await network.async_get_adapters(hass)

    local_ips = []
    for adapter in adapters:
        if not adapter["enabled"]:
            continue
        local_ips.extend([ip_info["address"] for ip_info in adapter["ipv4"]])

    return local_ips


class _UdpProto(asyncio.DatagramProtocol):
    """Asyncio protocol handler for receiving UDP discovery replies. Ignores packets from the local host and stores unique devices by IP."""

    def __init__(self, local_ips: list[str]) -> None:
        """Init protocol."""
        self.local_ips = local_ips
        self.by_ip: dict[str, dict[str, Any]] = {}

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        ip, port = addr
        # Ignore own packets
        if ip in self.local_ips:
            return
        name = _parse_name_from_reply(data)
        # Store first discovery from each IP
        self.by_ip.setdefault(
            ip,
            {
                "ip": ip,
                "port": port,
                "name": name,
                "raw": data,  # raw response bytes
            },
        )


async def _discover_broadcast(
    hass: HomeAssistant,
    broadcast_ip: str,
    probe: bytes,
    local_ips: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Send a single round of discovery probes and collect responses.

    Returns a list of device info dicts.
    """
    loop = asyncio.get_running_loop()

    # Create a UDP socket with broadcast enabled
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 0))  # ephemeral source port
    transport, proto = await loop.create_datagram_endpoint(
        lambda: _UdpProto(local_ips or []), sock=sock
    )
    try:
        # Send the probe multiple times to increase reliability
        for _ in range(DISCOVERY_RETRIES):
            transport.sendto(probe, (broadcast_ip, DISCOVERY_PORT))
            await asyncio.sleep(DISCOVERY_INTERVAL)
        # Wait for any remaining replies
        await asyncio.sleep(DISCOVERY_LISTEN_TIMEOUT)
        return list(proto.by_ip.values())
    finally:
        transport.close()
        await asyncio.sleep(0.05)


async def _discover_unicast_sweep(
    hass: HomeAssistant, base_ip: str, probe: bytes
) -> list[dict[str, Any]]:
    """Send unicast-probe to the entire /24 subnet based on base_ip and listen for replies."""
    parts = base_ip.split(".")
    subnet = ".".join(parts[:3])
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 0))
    transport, proto = await loop.create_datagram_endpoint(
        lambda: _UdpProto(["0.0.0.0"]), sock=sock
    )
    try:
        for host in range(1, 255):
            transport.sendto(probe, (f"{subnet}.{host}", DISCOVERY_PORT))
            await asyncio.sleep(0.002)  # let pacing
        await asyncio.sleep(DISCOVERY_LISTEN_TIMEOUT)
        return list(proto.by_ip.values())
    finally:
        transport.close()
        await asyncio.sleep(0.05)


# --- Public API ---------------------------------------------------------------


async def async_discover(
    hass: HomeAssistant,
    last_known_ip: str | None = None,
    broadcast_ip: str | None = None,
    include_raw: bool = False,
) -> list[dict[str, Any]]:
    """Discover Dantherm/Pluggit devices on all local networks.

    Tries broadcast and unicast sweep on all local IPs/subnets, then (if needed)
    on the last known subnet, and finally global broadcast. Handles cases where
    Home Assistant or the device has changed subnet or interface.
    """
    devices_by_ip: dict[str, dict[str, Any]] = {}

    # Helper function to add discovered devices
    def _add_discovered_devices(
        results: list[dict[str, Any]],
    ) -> None:
        """Add discovered devices to the devices_by_ip dictionary."""
        for d in results:
            devices_by_ip[d["ip"]] = {"ip": d["ip"], "name": d.get("name")}
            if include_raw:
                devices_by_ip[d["ip"]]["raw"] = d.get("raw")

    local_ips = await _async_get_local_ips(hass)
    _LOGGER.debug("Discovery: local IPs found: %s", local_ips)

    # Try broadcast on all detected subnets
    for ha_ip in local_ips:
        ha_subnet = _get_subnet(ha_ip)
        bcast = broadcast_ip or _get_broadcast(ha_ip)
        if bcast:
            _LOGGER.info(
                "Discovery: using broadcast %s (HA subnet %s)", bcast, ha_subnet
            )
            results = await _discover_broadcast(hass, bcast, PROBE_UUID, local_ips)
            _add_discovered_devices(results)
        if devices_by_ip:
            break  # Stop after first successful subnet

    # If nothing found and last_known_ip is present on a different subnet, try that subnet
    if not devices_by_ip and last_known_ip:
        try:
            last_subnet = _get_subnet(last_known_ip)
            if all(_get_subnet(ip) != last_subnet for ip in local_ips):
                bcast_last = _get_broadcast(last_known_ip)
                _LOGGER.info(
                    "Discovery: trying broadcast %s (last known subnet %s)",
                    bcast_last,
                    last_subnet,
                )
                results = await _discover_broadcast(
                    hass, bcast_last, PROBE_UUID, local_ips
                )
                _add_discovered_devices(results)

                # Optionally, try unicast sweep on last subnet if nothing found yet
                if not results:
                    _LOGGER.info(
                        "Discovery: trying unicast sweep on last known subnet %s.0/24",
                        last_subnet,
                    )
                    results = await _discover_unicast_sweep(
                        hass, last_known_ip, PROBE_UUID
                    )
                    _add_discovered_devices(results)
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Could not parse last_known_ip %s for subnet discovery", last_known_ip
            )

    # Fallback: try unicast sweep on all local subnets if nothing found yet
    if not devices_by_ip:
        _LOGGER.info(
            "No devices found via broadcast; trying unicast sweep on all local subnets"
        )
        for ha_ip in local_ips:
            ha_subnet = _get_subnet(ha_ip)
            _LOGGER.info("- Trying unicast sweep on subnet %s.0/24", ha_subnet)
            results = await _discover_unicast_sweep(hass, ha_ip, PROBE_UUID)
            _add_discovered_devices(results)
            if devices_by_ip:
                break

    # Optionally, try global broadcast as a last resort
    if not devices_by_ip:
        _LOGGER.info(
            "No devices found; trying global broadcast %s", DISCOVERY_BROADCAST_DEFAULT
        )
        results = await _discover_broadcast(
            hass, DISCOVERY_BROADCAST_DEFAULT, PROBE_UUID, local_ips
        )
        _add_discovered_devices(results)

    if not devices_by_ip:
        _LOGGER.info("No Dantherm/Pluggit devices found on the network")

    return list(devices_by_ip.values())
