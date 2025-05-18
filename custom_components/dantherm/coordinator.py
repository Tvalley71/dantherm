"""Coordinator implementation."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .device_map import DanthermEntityDescription
from .store import DanthermStore

_LOGGER = logging.getLogger(__name__)


class DanthermCoordinator(DataUpdateCoordinator, DanthermStore):
    """Read/write-coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        name,
        hub,
        scan_interval: int = 30,
        write_delay: float = 0.3,
    ) -> None:
        """Init coordinator."""
        DataUpdateCoordinator.__init__(
            self,
            hass,
            _LOGGER,
            name=f"{name}Coordinator",
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=scan_interval),
        )
        DanthermStore.__init__(
            self,
            hass,
            name,
        )
        self._attr_name = name
        self.hub = hub
        self._attr_available = True
        self._write_delay = write_delay
        self._entities = []

        # High-level queue "frontend" actions
        self._frontend_queue: asyncio.Queue = asyncio.Queue()
        # Low-level "backend" (modbus)
        self._backend_queue: deque = deque()
        # Lock to prevent reads/writes overlapping
        self._rw_lock = asyncio.Lock()
        # Event to wake backend processor
        self._backend_event = asyncio.Event()

        # Start processors
        hass.loop.create_task(self._process_frontend())
        hass.loop.create_task(self._process_backend())

    async def _async_update_data(self) -> dict:
        """Read all entities."""

        # Check if any entities is installed
        if not self._entities:
            return {}

        async with self._rw_lock:
            _LOGGER.debug(
                "<<< UPDATE BEGIN - %s >>>", datetime.now().strftime("%H:%M:%S.%f")
            )

            # Read current unit mode
            result = await self.hub.async_get_current_unit_mode()
            if result is None:
                if self.last_update_success != self._attr_available:
                    for entity in self._entities:
                        entity.async_write_ha_state()
                    self._attr_available = False
                raise UpdateFailed("Problem reading from modbus device")

            self._attr_available = True

            # Read active unit mode
            await self.hub.async_get_active_unit_mode()

            # Read fan level
            await self.hub.async_get_fan_level()

            # Read alarm
            await self.hub.async_get_alarm()

            data = {}
            for entity in self._entities:
                await self.async_update_entity(entity, data)

            await self.hub.async_update_adaptive_triggers()

            _LOGGER.debug(
                "<<< UPDATE END - %s >>>", datetime.now().strftime("%H:%M:%S.%f")
            )

        return data

    # ────────────── FRONTEND ─────────────────

    def enqueue_frontend(self, coro_func, *args, **kwargs) -> asyncio.Future:
        """Schedule a high-level coroutine to run “one at a time.

        Returns a Future you can await, or ignore if you want fire-and-forget.
        """
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        # enqueue with its own future
        self._frontend_queue.put_nowait((coro_func, args, kwargs, fut))
        return fut

    async def _process_frontend(self) -> None:
        """Run frontend tasks in sequence, waiting for backend writes after each."""
        while True:
            func, args, kwargs, fut = await self._frontend_queue.get()
            try:
                _LOGGER.debug("Frontend: executing %s", func.__name__)
                # run the user-level coroutine
                result = await func(*args, **kwargs)
                # then wait for all backend writes to finish
                await self._wait_for_backend_drain()
                # finally, set the future’s result
                fut.set_result(result)
            except Exception as exc:  # noqa: BLE001
                fut.set_exception(exc)
            finally:
                self._frontend_queue.task_done()

    async def _wait_for_backend_drain(self):
        """Pause until the backend queue is fully empty."""
        while self._backend_queue:
            # Sleep a fraction of write_delay to poll the queue
            await asyncio.sleep(self._write_delay / 2)

    # ────────────── BACKEND ──────────────────

    async def _process_backend(self):
        """Sequentially execute raw Modbus writes with locking + delay."""
        while True:
            # Wait until at least one write is enqueued
            await self._backend_event.wait()
            func, args, kwargs, fut = self._backend_queue.popleft()
            if not self._backend_queue:
                self._backend_event.clear()

            async with self._rw_lock:
                try:
                    _LOGGER.debug("Backend: writing %s", func.__name__)
                    result = await func(*args, **kwargs)
                    if fut:
                        fut.set_result(result)
                except Exception as exc:
                    _LOGGER.exception("Backend write failed")
                    if fut:
                        fut.set_exception(exc)
                await asyncio.sleep(self._write_delay)

    def enqueue_backend(self, func, *args, **kwargs):
        """Enqueue a low‐level corotine with locking + delay.

        Returns a Future you can await if you need to know when it completes,
        """
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._backend_queue.append((func, args, kwargs, fut))
        self._backend_event.set()
        return fut

    async def async_add_entity(self, entity):
        """Add entity for update."""

        _LOGGER.debug("Adding entity=%s", entity.key)
        self._entities.append(entity)

    async def async_remove_entity(self, entity):
        """Remove entity from update."""

        if entity.key in self.data:
            self.data.pop(entity.key)
        if entity in self._entities:
            self._entities.remove(entity)

        if (
            not self._entities
        ):  # disconnect and close modbus connection if no more entities
            await self.hub.disconnect_and_close()

    def is_entity_installed(self, key: str) -> bool:
        """Check if the entity with the key is installed."""
        return any(entity.key == key for entity in self._entities)

    async def async_update_entity(self, entity: Entity, data):
        """Update the entity."""

        description: DanthermEntityDescription = entity.entity_description

        if description.data_getavailable:
            if not getattr(
                self.hub, f"get_{description.data_getavailable}_available", True
            ):
                return data

        entity_data = await self.async_get_entity_data(description)
        if entity_data is not None:
            data.update({description.key: entity_data})

        return data

    async def async_restore_entity_state(self, entity: Entity, last_state: Any) -> None:
        """Restore the entity."""

        description: DanthermEntityDescription = entity.entity_description

        if last_state is None:
            return
        self.data.update({description.key: {"state": last_state}})
        entity.async_write_ha_state()

    async def async_set_entity_state(self, entity: Entity, state: Any) -> Any:
        """Schedule a write via the internal queue and update the cached data immediately."""

        description: DanthermEntityDescription = entity.entity_description

        # Enqueue frontent corotine
        fut = self.enqueue_frontend(self._async_set_entity_state, entity, state)

        # Update the in-memory cache
        self.data.update(
            {
                description.key: {
                    "state": state,
                    "icon": entity.icon,
                    "attrs": entity.extra_state_attributes,
                }
            }
        )

        return await fut

    async def async_get_entity_data(
        self, description: DanthermEntityDescription
    ) -> Any:
        """Get entity data from description, state, icon and attributes."""

        state = None
        if description.data_getinternal:
            if hasattr(self.hub, f"get_{description.data_getinternal}"):
                state = getattr(self.hub, f"get_{description.data_getinternal}")
            else:
                state = await getattr(
                    self.hub, f"async_get_{description.data_getinternal}"
                )()
        elif description.data_address:
            state = await self.hub.read_holding_registers(description=description)
        else:
            state = self.get_stored_entity_state(
                description.key, description.data_default
            )

        icon = None
        if hasattr(self.hub, f"get_{description.key}_icon"):
            icon = getattr(self.hub, f"get_{description.key}_icon")
        elif description.icon_zero:
            if not state:
                icon = description.icon_zero
            elif description.icon:
                icon = description.icon

        attrs = None
        if hasattr(self.hub, f"get_{description.key}_attrs"):
            attrs = getattr(self.hub, f"get_{description.key}_attrs")
        elif hasattr(self.hub, f"async_get_{description.key}_attrs"):
            attrs = getattr(self.hub, f"async_get_{description.key}_attrs")

        if state is not None:
            return {"state": state, "icon": icon, "attrs": attrs}
        return None

    async def _async_set_entity_state(self, entity: Entity, state):
        """Set entity state."""

        description: DanthermEntityDescription = entity.entity_description

        if description.data_setinternal:
            await getattr(self.hub, f"set_{description.data_setinternal}")(state)
        elif description.data_address and description.data_setaddress:
            await self.hub.write_holding_registers(description=description, value=state)
        else:
            await self.async_store_entity_state(entity.key, state)

        entity.async_write_ha_state()
