"""Dantherm discovery implementation."""

# Dantherm / Pluggit discovery helper for Home Assistant
# - Sends a UDP broadcast on port 6400 with a known UUID probe

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

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


def _guess_broadcast_from_local(local_ip: str) -> str:
    """Guess a /24 broadcast address based on the local IP.

    Falls back to DISCOVERY_BROADCAST_DEFAULT on error.
    """
    try:
        parts = local_ip.split(".")
        parts[-1] = "255"
        return ".".join(parts)
    except Exception:  # noqa: BLE001
        return DISCOVERY_BROADCAST_DEFAULT


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


class _UdpProto(asyncio.DatagramProtocol):
    """Asyncio protocol handler for receiving UDP discovery replies. Ignores packets from the local host and stores unique devices by IP."""

    def __init__(self, local_ip: str) -> None:
        """Init protocol."""
        self.local_ip = local_ip
        self.by_ip: dict[str, dict[str, Any]] = {}

    def datagram_received(self, data: bytes, addr) -> None:
        ip, port = addr
        # Ignore own packets
        if ip == self.local_ip:
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
    hass: HomeAssistant, broadcast_ip: str, probe: bytes
) -> list[dict[str, Any]]:
    """Send a single round of discovery probes and collect responses.

    Returns a list of device info dicts.
    """
    local_ip = hass.config.api.local_ip
    loop = asyncio.get_running_loop()

    # Create a UDP socket with broadcast enabled
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 0))  # ephemeral source port
    transport, proto = await loop.create_datagram_endpoint(
        lambda: _UdpProto(local_ip), sock=sock
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
        lambda: _UdpProto("0.0.0.0"), sock=sock
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
    """Broadcast discovery or fallback to unicast sweep if needed."""
    hint_ip = last_known_ip or hass.config.api.local_ip
    bcast = broadcast_ip or _guess_broadcast_from_local(hint_ip)
    _LOGGER.info("Discovery: using bcast %s (hint %s)", bcast, hint_ip)

    devices_by_ip: dict[str, dict[str, Any]] = {}
    results = await _discover_broadcast(hass, bcast, PROBE_UUID)

    # Fallback hvis broadcast ikke gav noget
    if not results:
        _LOGGER.debug(
            "No devices via broadcast; trying unicast sweep on %s/24", hint_ip
        )
        results = await _discover_unicast_sweep(hass, hint_ip, PROBE_UUID)

    for d in results:
        ip = d["ip"]
        if ip not in devices_by_ip:
            devices_by_ip[ip] = {"ip": ip, "name": d.get("name")}
            if include_raw:
                devices_by_ip[ip]["raw"] = d.get("raw")

    return list(devices_by_ip.values())
