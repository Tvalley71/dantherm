"""Coordinator implementation."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import now as ha_now

from .device_map import (
    ACTION_PENDING_MIN_READ_DELAY_MILLISECONDS,
    ATTR_ACTIONS_PENDING,
    ATTR_CALENDAR,
    BINARY_SENSORS,
    BUTTONS,
    COVERS,
    FANS,
    NUMBERS,
    SELECTS,
    SENSORS,
    SWITCHES,
    TIMETEXTS,
    DanthermEntityDescription,
    DanthermSwitchEntityDescription,
)
from .store import DanthermStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class PendingActionState:
    """Track pending write lifecycle for an entity."""

    requested_at: Any
    executed_at: Any | None = None
    executed_read_cycle: int | None = None


class DanthermCoordinator(DataUpdateCoordinator, DanthermStore):
    """Read/write-coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        hub: Any,  # DanthermDevice - avoiding circular import
        scan_interval: int,
        config_entry: ConfigEntry,
        write_delay: float = 0.3,
    ) -> None:
        """Init coordinator."""
        DataUpdateCoordinator.__init__(
            self,
            hass,
            _LOGGER,
            name=f"{name}Coordinator",
            update_method=self._update_data,
            update_interval=timedelta(seconds=scan_interval),
            config_entry=config_entry,
        )
        DanthermStore.__init__(
            self,
            hass,
            name,
        )
        self._attr_name = name
        self.hub = hub
        self._config_entry = config_entry
        self._write_delay = write_delay
        self._attr_available = True
        self._entities: list[Entity] = []

        # Flag to reload the integration on next update
        self._reload_on_update = False

        # High-level queue "frontend" actions
        self._frontend_queue: asyncio.Queue[
            tuple[Any, tuple[Any, ...], dict[str, Any], asyncio.Future[Any]]
        ] = asyncio.Queue()
        # Low-level "backend" (modbus)
        self._backend_queue: deque[
            tuple[Any, tuple[Any, ...], dict[str, Any], asyncio.Future[Any]]
        ] = deque()
        # Lock to prevent reads/writes overlapping
        self._rw_lock = asyncio.Lock()
        # Event to wake backend processor
        self._backend_event = asyncio.Event()
        self._backend_busy = False
        self._shutdown_requested = False

        # Pending action tracking
        self._pending_actions: dict[str, PendingActionState] = {}
        self._pending_supported_keys: set[str] = set()
        self._update_cycle = 0
        self._pending_min_read_delay = timedelta(
            milliseconds=ACTION_PENDING_MIN_READ_DELAY_MILLISECONDS
        )

        # Flat lookup of all statically-defined entity descriptions by key.
        # Used as a fallback write path when an entity is disabled (not instantiated).
        self._all_descriptions: dict[str, DanthermEntityDescription] = {
            desc.key: desc
            for tuple_ in (
                BINARY_SENSORS,
                BUTTONS,
                COVERS,
                FANS,
                NUMBERS,
                SELECTS,
                SENSORS,
                SWITCHES,
                TIMETEXTS,
            )
            for desc in tuple_
        }

        # Start processors
        self._frontend_task = hass.loop.create_task(self._process_frontend())
        self._backend_task = hass.loop.create_task(self._process_backend())

    async def async_shutdown(self) -> None:
        """Stop background queue processors and fail queued work."""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        await super().async_shutdown()

        while not self._frontend_queue.empty():
            _, _, _, fut = self._frontend_queue.get_nowait()
            if not fut.done():
                fut.cancel()
            self._frontend_queue.task_done()

        while self._backend_queue:
            _, _, _, fut = self._backend_queue.popleft()
            if not fut.done():
                fut.cancel()

        self._backend_event.set()

        tasks = [
            task
            for task in (self._frontend_task, self._backend_task)
            if not task.done()
        ]
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def schedule_reload(self) -> None:
        """Flag the integration to reload on the next update."""
        self._reload_on_update = True

    @staticmethod
    def _is_action_description(description: DanthermEntityDescription) -> bool:
        """Return True when an entity description supports write actions."""
        return bool(description.data_setinternal or description.data_setaddress)

    def is_entity_pending(self, entity_key: str) -> bool:
        """Return True when an entity currently has a pending action."""
        return entity_key in self._pending_actions

    def has_pending_actions(self) -> bool:
        """Return True when the device has pending actions."""
        return bool(self._pending_actions)

    def supports_pending(self, entity_key: str) -> bool:
        """Return True when an entity key supports the pending attribute."""
        return entity_key in self._pending_supported_keys

    def _inject_pending_attr(self, entity_key: str, attrs: Any) -> Any:
        """Add pending attribute to supported entities."""
        if not self.supports_pending(entity_key):
            return attrs

        result: dict[str, Any]
        if isinstance(attrs, dict):
            result = dict(attrs)
        else:
            result = {}

        result["pending"] = self.is_entity_pending(entity_key)
        return result

    def _mark_pending_requested(self, entity_key: str) -> None:
        """Mark an action as queued/requested for an entity."""
        self._pending_actions[entity_key] = PendingActionState(requested_at=ha_now())

    def _mark_pending_executed(self, entity_key: str) -> None:
        """Mark that an action has been executed in the communicator."""
        pending_state = self._pending_actions.get(entity_key)
        if pending_state is None:
            pending_state = PendingActionState(requested_at=ha_now())
            self._pending_actions[entity_key] = pending_state

        pending_state.executed_at = ha_now()
        pending_state.executed_read_cycle = self._update_cycle

    def _clear_pending(self, entity_key: str) -> None:
        """Clear pending state for a key."""
        self._pending_actions.pop(entity_key, None)

    def _process_pending_transitions(self) -> None:
        """Clear pending states after post-execute delay and a later read cycle."""
        now = ha_now()

        for entity_key, pending_state in list(self._pending_actions.items()):
            if (
                pending_state.executed_at is None
                or pending_state.executed_read_cycle is None
            ):
                continue

            if self._update_cycle <= pending_state.executed_read_cycle:
                continue

            if now < pending_state.executed_at + self._pending_min_read_delay:
                continue

            self._pending_actions.pop(entity_key, None)

    def _write_pending_aware_states(
        self, source_entity: Entity | None, entity_key: str
    ) -> None:
        """Refresh and write updated states for affected entities."""
        entities_to_refresh: list[Entity] = []

        if source_entity is not None:
            entities_to_refresh.append(source_entity)

        for entity in self._entities:
            key = getattr(entity, "key", entity.entity_id)
            if (
                key in (ATTR_ACTIONS_PENDING, entity_key)
                and entity not in entities_to_refresh
            ):
                entities_to_refresh.append(entity)

        for entity in entities_to_refresh:
            handle_coordinator_update = getattr(
                entity, "_handle_coordinator_update", None
            )
            if callable(handle_coordinator_update):
                handle_coordinator_update()
            else:
                entity.async_write_ha_state()

    async def _update_data(self) -> dict:
        """Read all entities."""

        # Check if any entities is installed
        if not self._entities:
            return {}

        # Keep adaptive event stack current before building entity states.
        # This avoids a one-cycle delay where expired events still appear in
        # adaptive state sensors.
        await self.hub.async_process_expired_events()
        await self.hub.async_update_adaptive_triggers()

        # Calendar updates may also trigger writes through adaptive handling.
        # Run them outside _rw_lock to avoid lock inversion with the backend writer.
        if any(getattr(entity, "key", entity.entity_id) == ATTR_CALENDAR for entity in self._entities):
            await self.hub.async_get_calendar()

        data: dict[str, Any] = {}

        async with self._rw_lock:
            _LOGGER.debug("<<< UPDATE BEGIN - %s >>>", ha_now().strftime("%H:%M:%S.%f"))

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

            # Read sensor filtering, make sure we have the latest value
            await self.hub.async_get_sensor_filtering()

            # Read bypass maximum temperature
            await self.hub.async_get_bypass_maximum_temperature()

            self._update_cycle += 1
            self._process_pending_transitions()
            for entity in self._entities:
                await self.async_update_entity(entity, data)

            config_entry_id = self._config_entry.entry_id
            # If flagged, reload the integration after fetching new data
            if self._reload_on_update:
                _LOGGER.debug(
                    "Reloading integration for config entry ID: %s",
                    config_entry_id,
                )

                # Schedule the reload of the config entry
                self.hass.config_entries.async_schedule_reload(config_entry_id)

                # Reset the flag
                self._reload_on_update = False

            _LOGGER.debug("<<< UPDATE END - %s >>>", ha_now().strftime("%H:%M:%S.%f"))

        return data

    # ────────────── FRONTEND ─────────────────

    def enqueue_frontend(
        self, coro_func: Any, *args: Any, **kwargs: Any
    ) -> asyncio.Future[Any]:
        """Schedule a high-level coroutine to run "one at a time.

        Returns a Future you can await, or ignore if you want fire-and-forget.
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        # enqueue with its own future
        self._frontend_queue.put_nowait((coro_func, args, kwargs, fut))
        return fut

    async def _process_frontend(self) -> None:
        """Run frontend tasks in sequence, waiting for backend writes after each."""
        while True:
            try:
                func, args, kwargs, fut = await self._frontend_queue.get()
            except asyncio.CancelledError:
                return
            try:
                _LOGGER.debug("Frontend: executing %s", func.__name__)
                # run the user-level coroutine
                result = await func(*args, **kwargs)
                # then wait for all backend writes to finish
                await self._wait_for_backend_drain()
                # finally, set the future’s result
                if not fut.done():  # check if future is not already done (e.g. by a timeout/exception/cancellation)
                    fut.set_result(result)
            except asyncio.CancelledError:
                if not fut.done():
                    fut.cancel()
                raise
            except Exception as exc:
                if not fut.done():  # check if future is not already done
                    fut.set_exception(exc)
                _LOGGER.exception("Frontend task failed: %s", func.__name__)
            finally:
                self._frontend_queue.task_done()

    async def _wait_for_backend_drain(self) -> None:
        """Pause until the backend queue is fully empty and idle."""
        while self._backend_queue or self._backend_busy:
            # Sleep a fraction of write_delay to poll the queue
            await asyncio.sleep(self._write_delay / 2)

    # ────────────── BACKEND ──────────────────

    async def _process_backend(self) -> None:
        """Sequentially execute raw Modbus writes with locking + delay."""
        while True:
            # Wait until at least one write is enqueued
            try:
                await self._backend_event.wait()
            except asyncio.CancelledError:
                return

            if not self._backend_queue:
                if self._shutdown_requested:
                    return
                self._backend_event.clear()
                continue

            func, args, kwargs, fut = self._backend_queue.popleft()
            if not self._backend_queue:
                self._backend_event.clear()

            self._backend_busy = True
            try:
                async with self._rw_lock:
                    try:
                        _LOGGER.debug("Backend: writing %s", func.__name__)
                        result = await func(*args, **kwargs)
                        if fut:
                            fut.set_result(result)
                    except asyncio.CancelledError:
                        if fut and not fut.done():
                            fut.cancel()
                        raise
                    except Exception as exc:
                        _LOGGER.exception("Backend write failed")
                        if fut:
                            fut.set_exception(exc)
                    await asyncio.sleep(self._write_delay)
            finally:
                self._backend_busy = False

    def enqueue_backend(
        self, func: Any, *args: Any, **kwargs: Any
    ) -> asyncio.Future[Any]:
        """Enqueue a low‐level coroutine with locking + delay.

        Returns a Future you can await if you need to know when it completes,
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self._backend_queue.append((func, args, kwargs, fut))
        self._backend_event.set()
        return fut

    async def async_add_entity(self, entity: Entity) -> None:
        """Add entity for update."""

        _LOGGER.debug("Adding entity=%s", getattr(entity, "key", entity.entity_id))
        self._entities.append(entity)
        description = getattr(entity, "entity_description", None)
        if isinstance(
            description, DanthermEntityDescription
        ) and self._is_action_description(description):
            self._pending_supported_keys.add(description.key)

    async def async_remove_entity(self, entity: Entity) -> None:
        """Remove entity from update."""

        entity_key = getattr(entity, "key", entity.entity_id)
        if entity_key in self.data:
            self.data.pop(entity_key)
        if entity in self._entities:
            self._entities.remove(entity)

        if (
            not self._entities
        ):  # disconnect and close modbus connection if no more entities
            await self.async_shutdown()
            await self.hub.disconnect_and_close()

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by key."""

        for entity in self._entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    def is_entity_installed(self, key: str) -> bool:
        """Check if the entity with the key is installed."""
        return any(
            getattr(entity, "key", entity.entity_id) == key for entity in self._entities
        )

    async def async_update_entity(
        self, entity: Entity, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update the entity."""

        description = getattr(entity, "entity_description", None)
        if not isinstance(description, DanthermEntityDescription):
            return data

        entity_data = await self.async_get_entity_data(description)
        if entity_data is not None:
            data.update({description.key: entity_data})

        return data

    async def async_restore_entity_state(self, entity: Entity, last_state: Any) -> None:
        """Restore the entity."""

        description = getattr(entity, "entity_description", None)
        if not isinstance(description, DanthermEntityDescription):
            return

        if last_state is None:
            return
        self.data.update({description.key: {"state": last_state}})
        entity.async_write_ha_state()

    async def async_set_entity_state_from_entity_id(
        self, entity_id: str, state: Any
    ) -> Any:
        """Schedule a set entity state from entity id via the internal queue and update the cached data immediately."""

        entity = self.get_entity(entity_id)
        if entity:
            await self.async_set_entity_state(entity, state)

    async def async_set_entity_state_by_key(self, entity_key: str, state: Any) -> Any:
        """Schedule a set entity state by entity key, including pending support."""
        entity = next(
            (e for e in self._entities if getattr(e, "key", e.entity_id) == entity_key),
            None,
        )
        if entity is not None:
            return await self.async_set_entity_state(entity, state)

        # Fallback: entity may be disabled in the entity registry.
        # Look up its static description and execute the write directly.
        description = self._all_descriptions.get(entity_key)
        if description is not None:
            _LOGGER.debug(
                "Entity key=%s has no instantiated entity (may be disabled); "
                "executing write via description fallback",
                entity_key,
            )

            if self.supports_pending(entity_key):
                self._mark_pending_requested(entity_key)
                self._write_pending_aware_states(None, entity_key)

            fut = self.enqueue_frontend(
                self._set_entity_state_by_description, description, entity_key, state
            )
            result = await fut

            if self.supports_pending(entity_key):
                self._mark_pending_executed(entity_key)
                self._write_pending_aware_states(None, entity_key)

            return result

        raise HomeAssistantError(
            f"Cannot set state for entity key '{entity_key}': "
            "no instantiated entity or matching description found"
        )

    async def async_set_entity_state(self, entity: Entity, state: Any) -> Any:
        """Schedule a set entity state via the internal queue and update the cached data immediately."""

        description = getattr(entity, "entity_description", None)
        if not isinstance(description, DanthermEntityDescription):
            return None

        _LOGGER.debug(
            "Schedule set entity state for entity_id=%s to state=%s",
            entity.entity_id,
            state,
        )

        entity_key = getattr(entity, "key", entity.entity_id)

        # Mark action as pending immediately
        if self.supports_pending(entity_key):
            self._mark_pending_requested(entity_key)

        # Enqueue frontend coroutine
        fut = self.enqueue_frontend(self._set_entity_state, entity, state)

        # Update the in-memory cache (inject pending attr immediately)
        current_attrs = getattr(entity, "extra_state_attributes", None)
        updated_attrs = self._inject_pending_attr(entity_key, current_attrs)
        self.data.update(
            {
                description.key: {
                    "state": state,
                    "icon": getattr(entity, "icon", None),
                    "attrs": updated_attrs,
                }
            }
        )

        # Immediately notify the actions_pending binary sensor
        for ent in self._entities:
            if getattr(ent, "key", ent.entity_id) == ATTR_ACTIONS_PENDING:
                ent.async_write_ha_state()
                break

        return await fut

    async def async_get_entity_data(
        self, description: DanthermEntityDescription
    ) -> Any:
        """Get entity data from description, state, icon and attributes."""

        state = None
        if description.data_getavailable:
            if not getattr(self.hub, f"get_{description.data_getavailable}", True):
                return None
            if not getattr(
                self.hub, f"get_{description.data_getavailable}_available", True
            ):
                return None

        if description.data_getunknown and (
            getattr(self.hub, f"get_{description.data_getunknown}", False)
            or getattr(self.hub, f"get_{description.data_getunknown}_unknown", False)
        ):
            state = None
        elif description.data_getinternal:
            if description.key == ATTR_CALENDAR:
                state = self.get_stored_entity_state(
                    description.key, description.data_default
                )
            elif hasattr(self.hub, f"async_get_{description.data_getinternal}"):
                state = await getattr(
                    self.hub, f"async_get_{description.data_getinternal}"
                )()
            else:
                state = getattr(self.hub, f"get_{description.data_getinternal}")
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

        attrs = self._inject_pending_attr(description.key, attrs)
        return {"state": state, "icon": icon, "attrs": attrs}

    async def _set_entity_state(self, entity: Entity, state: Any) -> None:
        """Set entity state."""

        description = getattr(entity, "entity_description", None)
        if not isinstance(description, DanthermEntityDescription):
            return

        if isinstance(description, DanthermSwitchEntityDescription):
            if state == STATE_ON:
                state = True
            elif state == STATE_OFF:
                state = False

            if isinstance(state, bool):
                if state:
                    state = description.state_seton or description.state_on
                else:
                    state = description.state_setoff or description.state_off

        entity_key = getattr(entity, "key", entity.entity_id)
        if description.data_setinternal:
            await getattr(self.hub, f"set_{description.data_setinternal}")(state)
        elif description.data_address and description.data_setaddress:
            await self.hub.write_holding_registers(description=description, value=state)
        else:
            await self.async_store_entity_state(entity_key, state)

        if self.supports_pending(entity_key):
            self._mark_pending_executed(entity_key)
        self._write_pending_aware_states(entity, entity_key)

    async def _set_entity_state_by_description(
        self,
        description: DanthermEntityDescription,
        entity_key: str,
        state: Any,
    ) -> None:
        """Execute a write using only a description, without a live entity instance.

        Used as a fallback when the entity is disabled in the entity registry.
        HA state cannot be refreshed (the entity is not instantiated), but the
        underlying Modbus / internal write is still performed.
        """
        if isinstance(description, DanthermSwitchEntityDescription):
            if state == STATE_ON:
                state = True
            elif state == STATE_OFF:
                state = False

            if isinstance(state, bool):
                if state:
                    state = description.state_seton or description.state_on
                else:
                    state = description.state_setoff or description.state_off

        if description.data_setinternal:
            # Call the hub's named setter, e.g. hub.set_away_mode(state)
            await getattr(self.hub, f"set_{description.data_setinternal}")(state)
        elif description.data_address and description.data_setaddress:
            # Write value directly to the Modbus holding register
            await self.hub.write_holding_registers(description=description, value=state)
        else:
            # No hardware write path; persist value in the local store only
            await self.async_store_entity_state(entity_key, state)
