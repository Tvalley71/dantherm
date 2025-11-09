"""Test the Dantherm modbus functionality."""

from unittest.mock import AsyncMock, patch

from config.custom_components.dantherm.modbus import (
    MODBUS_REGISTER_ALARM,
    MODBUS_REGISTER_FAN_LEVEL,
    MODBUS_REGISTER_FILTER_REMAIN,
    MODBUS_REGISTER_OUTDOOR_TEMP,
    MODBUS_REGISTER_SERIAL_NUMBER,
    DanthermModbus,
)
import pytest


class TestDanthermModbus:
    """Test the DanthermModbus class."""

    async def test_specific_register_addresses(self):
        """Test that specific register addresses are correctly defined."""
        # Test that registers have expected values (these are from the actual implementation)
        assert MODBUS_REGISTER_ALARM == 516
        assert MODBUS_REGISTER_FAN_LEVEL == 324
        assert MODBUS_REGISTER_FILTER_REMAIN == 554
        assert MODBUS_REGISTER_OUTDOOR_TEMP == 132
        assert MODBUS_REGISTER_SERIAL_NUMBER == 4

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_initialization_parameters(self, mock_tcp_client):
        """Test DanthermModbus initialization with correct parameters."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test_device", "192.168.1.100", 502, 1)

        assert modbus._host == "192.168.1.100"
        assert modbus._port == 502
        assert modbus._unit_id == 1
        assert modbus._attr_available is False
        assert modbus._read_errors == 0

        # Verify client was created with correct parameters
        mock_tcp_client.assert_called_once_with(
            host="192.168.1.100", port=502, name="test_device", timeout=10
        )

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_ensure_connected_success(self, mock_tcp_client):
        """Test successful connection establishment."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)
        result = await modbus.ensure_connected()

        assert result is True
        assert modbus._attr_available is True

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_ensure_connected_failure(self, mock_tcp_client):
        """Test connection failure."""
        mock_client = AsyncMock()
        mock_client.connected = False
        mock_client.connect.return_value = False
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)
        result = await modbus.ensure_connected()

        assert result is False
        assert modbus._attr_available is False

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_read_holding_registers_unavailable(self, mock_tcp_client):
        """Test reading when client is unavailable."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with patch.object(modbus, "ensure_connected", return_value=False):
            result = await modbus.read_holding_registers(
                address=MODBUS_REGISTER_FAN_LEVEL
            )

            assert result is None

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_read_holding_registers_single_register(self, mock_tcp_client):
        """Test reading a single register."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with (
            patch.object(modbus, "ensure_connected", return_value=True),
            patch.object(modbus, "_read_holding_uint16", return_value=42),
        ):
            result = await modbus.read_holding_registers(
                address=MODBUS_REGISTER_FAN_LEVEL, count=1
            )

            assert result == 42

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_read_holding_registers_with_scale(self, mock_tcp_client):
        """Test reading with scale factor."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with (
            patch.object(modbus, "ensure_connected", return_value=True),
            patch.object(modbus, "_read_holding_uint16", return_value=10),
        ):
            result = await modbus.read_holding_registers(
                address=MODBUS_REGISTER_FAN_LEVEL, count=1, scale=2
            )

            assert result == 20  # 10 * 2

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_read_uint32_registers(self, mock_tcp_client):
        """Test reading uint32 registers (count=2)."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with (
            patch.object(modbus, "ensure_connected", return_value=True),
            patch.object(modbus, "_read_holding_uint32", return_value=12345),
        ):
            result = await modbus.read_holding_registers(
                address=MODBUS_REGISTER_SERIAL_NUMBER, count=2
            )

            assert result == 12345

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_write_holding_registers_success(self, mock_tcp_client):
        """Test successful writing to holding registers."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        # Mock coordinator to simulate successful enqueue
        mock_coordinator = AsyncMock()
        mock_coordinator.enqueue_backend = AsyncMock()
        modbus.coordinator = mock_coordinator

        with (
            patch.object(modbus, "ensure_connected", return_value=True),
            patch.object(
                modbus, "_DanthermModbus__write_holding_registers"
            ) as mock_write,
        ):
            result = await modbus.write_holding_registers(
                address=MODBUS_REGISTER_FAN_LEVEL, value=3
            )

            # The method doesn't return a value but should not raise an error
            assert result is None
            # Verify the direct write was called since coordinator is None
            mock_write.assert_called_once_with(324, [3])

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_write_holding_registers_with_scale(self, mock_tcp_client):
        """Test writing with scale factor."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        # Mock coordinator to simulate successful enqueue
        mock_coordinator = AsyncMock()
        mock_coordinator.enqueue_backend = AsyncMock()
        modbus.coordinator = mock_coordinator

        with (
            patch.object(modbus, "ensure_connected", return_value=True),
            patch.object(
                modbus, "_DanthermModbus__write_holding_registers"
            ) as mock_write,
        ):
            result = await modbus.write_holding_registers(
                address=MODBUS_REGISTER_FAN_LEVEL, value=5, scale=2
            )

            # Verify the method was called (scaling is handled internally)
            assert result is None
            # Verify the direct write was called with scaled value: 5 * 2 = 10
            mock_write.assert_called_once_with(324, [10])

    @patch("asyncio.sleep")  # Mock sleep to speed up test
    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_disconnect_and_close(self, mock_tcp_client, mock_sleep):
        """Test disconnection and closing."""
        mock_client = AsyncMock()
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)
        modbus._attr_available = True

        await modbus.disconnect_and_close()

        assert modbus._attr_available is False
        assert modbus._read_errors == 0
        assert modbus._client is None
        mock_client.close.assert_called_once()
        mock_sleep.assert_called_once_with(5)

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_connect_and_verify_success(self, mock_tcp_client):
        """Test successful connection and verification."""
        mock_client = AsyncMock()
        mock_client.connect.return_value = True
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with patch.object(modbus, "_read_holding_uint32", return_value=12345):
            result = await modbus.connect_and_verify()

            assert result == 12345
            assert modbus._attr_available is True
            mock_client.connect.assert_called_once()

    @patch("homeassistant.components.modbus.modbus.AsyncModbusTcpClient")
    async def test_connect_and_verify_connection_failure(self, mock_tcp_client):
        """Test connection failure during verification."""
        mock_client = AsyncMock()
        mock_client.connect.return_value = False
        mock_tcp_client.return_value = mock_client

        modbus = DanthermModbus("test", "192.168.1.100", 502, 1)

        with pytest.raises(ValueError, match="Modbus setup failed"):
            await modbus.connect_and_verify()
