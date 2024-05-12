"""Device implementation."""

import asyncio
from datetime import datetime, timedelta
import logging

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.modbus import modbus
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DEVICE_TYPES,
    DOMAIN,
    STATE_AUTOMATIC,
    STATE_MANUAL,
    STATE_STANDBY,
    STATE_WEEKPROGRAM,
    BypassDamperState,
    DataClass,
)

_LOGGER = logging.getLogger(__name__)


class DanthermEntity(Entity):
    """Dantherm Entity."""

    def __init__(
        self,
        device,
    ) -> None:
        """Initialize the instance."""
        self._device = device
        self.attr_suspend_refresh: datetime | None = None

    async def async_added_to_hass(self):
        """Register entity for refresh interval."""
        self._device.async_add_refresh_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister entity for refresh interval."""
        self._device.async_remove_refresh_entity(self)

    def suspend_refresh(self, seconds: int):
        """Suspend entity refresh for specified number of seconds."""

        self.attr_suspend_refresh = datetime.now() + timedelta(seconds=seconds)

    @property
    def key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"dantherm_{self.key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self.key

    @property
    def device_info(self):
        """Device Info."""
        unique_id = self._device.get_device_name + " " + self._device.get_device_type

        return {
            "identifiers": {
                (DOMAIN, unique_id),
            },
            "name": self._device.get_device_name,
            "manufacturer": "Dantherm",
            "model": self._device.get_device_type,
            "sw_version": self._device.get_device_fw_version,
            "serial_number": self._device.get_device_serial_number,
        }


class Device:
    """Dantherm Device."""

    def __init__(
        self,
        hass: HomeAssistant,
        name,
        host,
        port,
        unit_id,
        scan_interval,
    ) -> None:
        """Init device."""
        self._hass = hass
        self._device_name = name
        self._device_type = 0
        self._device_installed_components = 0
        self._device_fw_version = 0
        self._device_serial_number = 0
        self._host = host
        self._port = port
        self._unit_id = int(unit_id)
        self._client_config = {
            "name": self._device_name,
            "type": "tcp",
            "method": "rtu",
            "delay": 0,
            "port": self._port,
            "timeout": 1,
            "host": self._host,
        }
        self._modbus = modbus.ModbusHub(self._hass, self._client_config)
        self._scan_interval = timedelta(seconds=scan_interval)
        self._entity_refresh_method = None
        self._current_unit_mode = 0
        self._active_unit_mode = 0
        self._fan_level = 0
        self._alarm = 0
        self._bypass_damper = 0
        self._filter_lifetime = 0
        self._filter_remain = 0
        self._entities = []
        self.data = {}

    async def setup(self):
        """Modbus setup for Dantherm Device."""

        _LOGGER.debug("Setup has started")

        success = await self._modbus.async_setup()

        if success:
            task = [
                task
                for task in asyncio.all_tasks()
                if task.get_name() == "modbus-connect"
            ]
            await asyncio.wait(task, timeout=5)
            _LOGGER.debug("Modbus has been setup")
        else:
            await self._modbus.async_close()
            _LOGGER.error("Modbus setup was unsuccessful")
            raise ValueError("Modbus setup was unsuccessful")

        result = await self._read_holding_uint16(610)
        if result is None:
            raise ValueError("Dantherm unit probably not responding")

        self._device_installed_components = result
        _LOGGER.debug(
            "Installed components (610) = %s",
            hex(self._device_installed_components),
        )

        self._device_type = await self._read_holding_uint8(address=3)
        _LOGGER.debug("Device type = %s", self.get_device_type)
        self._device_fw_version = await self.read_holding_registers(address=24)
        _LOGGER.debug("Firmware version = %s", self.get_device_fw_version)
        self._device_serial_number = await self._read_holding_uint64(address=4)
        _LOGGER.debug("Serial number = %d", self.get_device_serial_number)

    async def async_install_entity(self, description: EntityDescription) -> bool:
        """Test if the component is installed on the device."""

        install = True
        if (description.component_class) and (
            (self._device_installed_components & description.component_class) == 0
        ):
            install = False
        if description.data_exclude_if is not None:
            result = await self.read_holding_registers(description=description)
            if description.data_exclude_if == result:
                install = False

        if install:
            return True
        _LOGGER.debug("Excluding an entity=%s", description.key)
        return False

    def async_add_refresh_entity(self, entity):
        """Add entity for refresh."""
        # This is the first entity, set up interval.
        if not self._entities:
            self._entity_refresh_method = async_track_time_interval(
                self._hass, self.async_refresh_entities, self._scan_interval
            )

        self._entities.append(entity)

    def async_remove_refresh_entity(self, entity):
        """Remove entity for refresh."""
        self._entities.remove(entity)

        if not self._entities:
            # This is the last entity, stop the interval timer
            self._entity_refresh_method()
            self._entity_refresh_method = None

    async def async_refresh_entities(self, _now: int | None = None) -> None:
        """Time to update entities."""

        if not self._entities:
            return

        _LOGGER.debug(
            "Installed components = %s", hex(self._device_installed_components)
        )

        self._current_unit_mode = await self._read_holding_uint32(472)
        _LOGGER.debug("Current unit mode = %s", hex(self._current_unit_mode))

        self._active_unit_mode = await self._read_holding_uint32(168)
        _LOGGER.debug("Active unit mode = %s", hex(self._active_unit_mode))

        self._fan_level = await self._read_holding_uint32(324)
        _LOGGER.debug("Fan level = %s", self._fan_level)

        self._alarm = await self._read_holding_uint32(516)
        _LOGGER.debug("Alarm = %s", self._alarm)

        self._bypass_damper = await self._read_holding_int32(198)
        _LOGGER.debug("Bypass damper = %s", self._bypass_damper)

        self._filter_lifetime = await self._read_holding_uint32(556)
        _LOGGER.debug("Filter lifetime = %s", self._filter_lifetime)

        self._filter_remain = await self._read_holding_uint32(554)
        _LOGGER.debug("Filter remain = %s", self._filter_remain)

        for entity in self._entities:
            await self.async_refresh_entity(entity)

    async def async_refresh_entity(self, entity: DanthermEntity) -> None:
        """Refresh an entity."""

        if entity.attr_suspend_refresh:
            if entity.attr_suspend_refresh < datetime.now():
                entity.attr_suspend_refresh = None
                _LOGGER.debug("Remove suspension of entity=%s", entity.name)
            else:
                _LOGGER.debug("Skipping suspened entity=%s", entity.name)
                return

        _LOGGER.debug("Refresh entity=%s", entity.name)

        await entity.async_update_ha_state(True)
        entity.async_write_ha_state()

    @property
    def get_current_unit_mode(self):
        """Get current unit mode."""

        return self._current_unit_mode

    @property
    def get_active_unit_mode(self):
        """Get active unit mode."""

        return self._active_unit_mode

    @property
    def get_operation_selection(self):
        """Get operation selection."""

        if self._active_unit_mode & 2 == 2:  # demand mode
            return STATE_AUTOMATIC
        if self._active_unit_mode & 4 == 4:  # manual mode
            if self._fan_level == 0:
                return STATE_STANDBY
            return STATE_MANUAL  # manual
        if self._active_unit_mode & 8 == 8:  # week program
            return STATE_WEEKPROGRAM

        _LOGGER.debug("Unknown mode of operation=%s", self._active_unit_mode)
        return STATE_MANUAL  # manual

    @property
    def get_fan_level_selection_icon(self) -> str:
        """Get fan level selection icon."""

        result = self.get_fan_level
        if not result:
            return "mdi:fan-off"
        if result == 1:
            return "mdi:fan-speed-1"
        if result == 2:
            return "mdi:fan-speed-2"
        if result == 3:
            return "mdi:fan-speed-3"
        return "mdi:fan-plus"

    @property
    def get_fan_level(self):
        """Get fan level."""

        return self._fan_level

    @property
    def get_fan_level_icon(self) -> str:
        """Get fan level icon."""

        if self._alarm != 0:
            return "mdi:fan-alert"
        result = self.get_operation_selection
        if result == STATE_STANDBY:
            return "mdi:fan-off"
        if result == STATE_AUTOMATIC:
            return "mdi:fan-auto"
        if result == STATE_WEEKPROGRAM:
            return "mdi:fan-clock"
        return "mdi:fan"

    @property
    def get_alarm(self):
        """Get alarm."""

        return self._alarm

    @property
    def get_bypass_damper(self):
        """Get bypass damper."""

        return self._bypass_damper

    @property
    def get_bypass_damper_icon(self) -> str:
        """Get bypass damper icon."""

        if self.get_bypass_damper == BypassDamperState.Closed:
            return "mdi:valve-closed"
        if self.get_bypass_damper == BypassDamperState.Opened:
            return "mdi:valve-open"
        return "mdi:valve"

    @property
    def get_filter_lifetime(self):
        """Get filter lifetime."""

        return self._filter_lifetime

    @property
    def get_filter_remain(self):
        """Get filter remain."""

        return self._filter_remain

    @property
    def get_filter_remain_attrs(self):
        """Get filter remain attributes."""

        if not self._filter_lifetime:
            return None
        return {
            "level": int(
                (self._filter_lifetime - self._filter_remain)
                / (self._filter_lifetime / 4)
            )
        }

    async def set_active_unit_mode(self, value):
        """Set active unit mode."""

        await self._write_holding_uint32(168, value)

    async def set_operation_selection(self, value):
        """Set operation mode selection."""

        if value == STATE_STANDBY:
            await self.set_active_unit_mode(4)  # manual mode
            if self._fan_level != 0:
                await self.set_fan_level(0)
        elif value == STATE_AUTOMATIC:
            await self.set_active_unit_mode(2)  # demand mode
        elif value == STATE_MANUAL:
            await self.set_active_unit_mode(4)  # manual mode
            if self._fan_level == 0:
                await self.set_fan_level(2)
        elif value == STATE_WEEKPROGRAM:
            await self.set_active_unit_mode(8)  # week program mode

    async def set_fan_level(self, value):
        """Set fan level."""

        await self._write_holding_uint32(324, value)

    async def set_filter_lifetime(self, value):
        """Set filter lifetime."""

        await self._write_holding_uint32(556, value)

    async def set_bypass_damper(self, feature: CoverEntityFeature = None):
        """Set bypass damper."""

        if self.get_active_unit_mode & 0x80 == 0x80:
            await self.set_active_unit_mode(0x8080)
        else:
            await self.set_active_unit_mode(0x80)

    async def read_holding_registers(
        self,
        description: EntityDescription | None = None,
        address: int | None = None,
        byteorder: Endian | None = None,
        wordorder: Endian | None = None,
        count=1,
        precision: int | None = None,
        scale=1,
    ):
        """Read modbus holding registers."""

        result = 0
        if description:
            if not address:
                address = description.data_address
            if description.data_class == DataClass.UInt8:
                result = await self._read_holding_uint8(address)
            elif description.data_class == DataClass.Int8:
                result = await self._read_holding_int8(address)
            elif description.data_class == DataClass.UInt16:
                result = await self._read_holding_uint16(address)
            elif description.data_class == DataClass.Int16:
                result = await self._read_holding_int16(address)
            elif description.data_class == DataClass.UInt32:
                result = await self._read_holding_uint32(address)
            elif description.data_class == DataClass.Int32:
                result = await self._read_holding_int32(address)
            elif description.data_class == DataClass.UInt64:
                result = await self._read_holding_uint64(address)
            elif description.data_class == DataClass.Float32:
                if not precision:
                    precision = description.data_precision
                result = await self._read_holding_float32(address, precision)
        elif address:
            data = await self._read_holding_registers(address, count)
            decoder = BinaryPayloadDecoder.fromRegisters(
                data.registers,
                byteorder or Endian.LITTLE,
                wordorder or Endian.LITTLE,
            )
            if count == 1:
                result = decoder.decode_16bit_uint()
            elif count == 2:
                result = decoder.decode_32bit_uint()
            elif count == 4:
                result = decoder.decode_64bit_uint()
        result *= scale
        _LOGGER.debug("Reading holding register=%s result=%s", str(address), result)
        return result

    async def write_holding_registers(
        self,
        description: EntityDescription | None = None,
        address: int | None = None,
        value: int = 0,
        scale=1,
    ):
        """Write modbus holding registers."""

        value *= scale
        if description:
            data_class = description.data_setclass
            if not data_class:
                data_class = description.data_class
            if not address:
                address = description.data_setaddress
            if not address:
                address = description.data_address
            if data_class == DataClass.UInt8:
                await self._write_holding_uint8(address, value)
            elif data_class == DataClass.Int8:
                await self._write_holding_int8(address, value)
            elif data_class == DataClass.UInt16:
                await self._write_holding_uint16(address, value)
            elif data_class == DataClass.Int16:
                await self._write_holding_int16(address, value)
            elif data_class == DataClass.UInt32:
                await self._write_holding_uint32(address, value)
            elif data_class == DataClass.Int32:
                await self._write_holding_int32(address, value)
            elif data_class == DataClass.Float32:
                await self._write_holding_float32(address, value)
        else:
            await self._write_holding_registers(address, value)

    @property
    def get_device_name(self) -> str:
        """Device name."""
        return self._device_name

    @property
    def get_device_type(self) -> str:
        """Device type."""

        result = DEVICE_TYPES.get(self._device_type, None)
        if result is None:
            result = f"UNKNOWN {self._device_type}"
        return result

    @property
    def get_device_fw_version(self) -> str:
        """Device firmware version."""
        minor = (self._device_fw_version >> 8) & 0xFF
        major = self._device_fw_version & 0xFF
        return f"({major}.{minor:02})"

    @property
    def get_device_serial_number(self) -> int:
        """Device serial number."""
        return self._device_serial_number

    async def _read_holding_registers(self, address, count):
        """Read holding registers."""

        result = await self._modbus.async_pb_call(
            self._unit_id, address, count, "holding"
        )
        if result is None:
            _LOGGER.error(
                "Error reading holding register=%s count=%s", str(address), str(count)
            )
        return result

    async def _write_holding_registers(self, address, values: list[int] | int):
        """Write holding registers."""

        result = await self._modbus.async_pb_call(
            self._unit_id,
            address,
            values,
            "write_registers",
        )
        if result is None:
            _LOGGER.error(
                "Error writing holding register=%s values=%s", str(address), str(values)
            )

    async def _read_holding_int8(self, address):
        """Read holding int8 registers."""

        result = await self._read_holding_registers(address, 1)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_8bit_int()

    async def _write_holding_int8(self, address, value):
        """Write holding int8 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_8bit_int(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint8(self, address):
        """Read holding uint8 registers."""

        result = await self._read_holding_registers(address, 1)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_8bit_uint()

    async def _write_holding_uint8(self, address, value):
        """Write holding uint8 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_8bit_uint(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_int16(self, address):
        """Read holding int16 registers."""

        result = await self._read_holding_registers(address, 1)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_16bit_int()

    async def _write_holding_int16(self, address, value):
        """Write holding int16 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_16bit_int(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint16(self, address):
        """Read holding uint16 registers."""

        result = await self._read_holding_registers(address, 1)
        if result is None:
            return None
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_16bit_uint()

    async def _write_holding_uint16(self, address, value):
        """Write holding uint16 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_16bit_uint(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_int32(self, address):
        """Read holding int32 registers."""

        result = await self._read_holding_registers(address, 2)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_32bit_int()

    async def _write_holding_int32(self, address, value):
        """Write holding int32 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_32bit_int(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint32(self, address):
        """Read holding uint32 registers."""

        result = await self._read_holding_registers(address, 2)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_32bit_uint()

    async def _write_holding_uint32(self, address, value):
        """Write holding uint32 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_32bit_uint(int(value))
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint64(self, address):
        """Read holding uint64 registers."""

        result = await self._read_holding_registers(address, 4)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        return decoder.decode_64bit_uint()

    async def _read_holding_float32(self, address, precision):
        """Read holding float32 registers."""

        result = await self._read_holding_registers(address, 2)
        decoder = BinaryPayloadDecoder.fromRegisters(
            result.registers, byteorder=Endian.BIG, wordorder=Endian.LITTLE
        )
        result = decoder.decode_32bit_float()
        if precision >= 0:
            result = round(result, precision)
        if precision == 0:
            result = int(result)
        return result

    async def _write_holding_float32(self, address, value):
        """Write holding float32 registers."""

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.LITTLE)
        builder.add_32bit_float(value)
        payload = builder.to_registers()
        await self._write_holding_registers(address, payload)
