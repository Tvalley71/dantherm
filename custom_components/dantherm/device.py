"""Device implementation."""

import asyncio
from datetime import timedelta
import logging

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from homeassistant.components.modbus import modbus
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import async_track_time_interval

from .const import DataClass

_LOGGER = logging.getLogger(__name__)


class Device:
    """Dantherm Device."""

    unit_id = 0

    def __init__(
        self,
        hass: HomeAssistant,
        name,
        host,
        port,
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
        self._entities = []
        self.data = {}

    async def setup(self):
        """Modbus setup for Dantherm Device."""

        _LOGGER.debug("Setup has started")

        Device.unit_id += 1
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

        self._device_installed_components = await self.read_holding_registers(
            address=610, count=2
        )
        _LOGGER.debug(
            "Installed components 2 = %s", hex(self._device_installed_components)
        )
        self._device_installed_components = await self.read_holding_registers(address=2)
        _LOGGER.debug(
            "Installed components 1 = %s", hex(self._device_installed_components)
        )
        self._device_type = await self.read_holding_registers(address=3)
        _LOGGER.debug("Device type = %s", hex(self._device_type))
        self._device_fw_version = await self.read_holding_registers(address=24)
        _LOGGER.debug("Firmware version = %s", self._device_fw_version)
        self._device_serial_number = await self.read_holding_registers(
            address=7, count=2
        )
        _LOGGER.debug("Serial number = %s", self._device_serial_number)

    async def async_install_entity(self, description: EntityDescription) -> bool:
        """Test if the component is installed on the device."""

        if (not description.component_class) or (
            (self._device_installed_components & description.component_class)
            == description.component_class
        ):
            if description.data_exclude_if is None:
                return True
            result = await self.read_holding_registers(description=description)
            if description.data_exclude_if == result:
                return False
            return True
        return False

    # @callback
    def async_add_refresh_entity(self, entity):
        """Add entity for refresh."""
        # This is the first sensor, set up interval.
        if not self._entities:
            self._entity_refresh_method = async_track_time_interval(
                self._hass, self.async_refresh_entities, self._scan_interval
            )

        self._entities.append(entity)

    # @callback
    def async_remove_refresh_entity(self, entity):
        """Remove entity for refresh."""
        self._entities.remove(entity)

        if not self._entities:
            # stop the interval timer upon removal of last sensor
            self._entity_refresh_method()
            self._entity_refresh_method = None

    async def async_refresh_entities(self, _now: int | None = None) -> None:
        """Time to update entities."""
        if not self._entities:
            return

        for entity in self._entities:
            await self.async_refresh_entity(entity=entity)

    async def async_refresh_entity(
        self, entity: Entity | None = None, name: str | None = None
    ) -> None:
        """Time to update entities."""

        if not entity:
            for entity in self._entities:
                if entity.name == name:
                    break

        if not entity:
            return

        await entity.async_update_ha_state(True)
        entity.async_write_ha_state()

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
        device_types = {
            1: "WG200",
            2: "WG300",
            3: "WG500",
            4: "HCC 2",
            5: "HCC 2 ALU",
            6: "HCV300 ALU",
            7: "HCV500 ALU",
            8: "HCV700 ALU",
            9: "HCV400 P2",
            10: "HCV400 E1",
            11: "HCV400 P1",
            12: "HCC 2 E1",
        }
        return device_types[self._device_type]

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
            Device.unit_id, address, count, "holding"
        )
        if result is None:
            _LOGGER.log(
                "Error reading holding register=%s count=%s", str(address), str(count)
            )
        return result

    async def _write_holding_registers(self, address, values: list[int] | int):
        """Write holding registers."""

        result = await self._modbus.async_pb_call(
            Device.unit_id,
            address,
            values,
            "write_registers",
        )
        if result is None:
            _LOGGER.log(
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
        """Read holding int8 registers."""

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

    async def _read_holding_float32(self, address, precision):
        """Read holding int registers."""

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
