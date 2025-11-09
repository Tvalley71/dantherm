"""Test the Dantherm exceptions module."""

from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.exceptions import (
    InvalidAdaptiveState,
    InvalidFilterLifetime,
    InvalidTimeFormat,
)
import pytest

from homeassistant.exceptions import HomeAssistantError


class TestInvalidTimeFormat:
    """Test InvalidTimeFormat exception."""

    def test_initialization(self) -> None:
        """Test exception initialization."""
        exception = InvalidTimeFormat()

        assert isinstance(exception, HomeAssistantError)
        assert exception.translation_domain == DOMAIN
        assert exception.translation_key == "invalid_timeformat"

    def test_inheritance(self) -> None:
        """Test exception inheritance."""
        exception = InvalidTimeFormat()
        assert isinstance(exception, HomeAssistantError)

    def test_raise_and_catch(self) -> None:
        """Test raising and catching InvalidTimeFormat."""
        with pytest.raises(InvalidTimeFormat) as exc_info:
            raise InvalidTimeFormat()

        assert exc_info.value.translation_domain == DOMAIN
        assert exc_info.value.translation_key == "invalid_timeformat"


class TestInvalidFilterLifetime:
    """Test InvalidFilterLifetime exception."""

    def test_initialization(self) -> None:
        """Test exception initialization."""
        exception = InvalidFilterLifetime()

        assert isinstance(exception, HomeAssistantError)
        assert exception.translation_domain == DOMAIN
        assert exception.translation_key == "invalid_filter_lifetime"

    def test_inheritance(self) -> None:
        """Test exception inheritance."""
        exception = InvalidFilterLifetime()
        assert isinstance(exception, HomeAssistantError)

    def test_custom_message(self) -> None:
        """Test exception with standard initialization."""
        exception = InvalidFilterLifetime()

        assert isinstance(exception, HomeAssistantError)
        assert exception.translation_domain == DOMAIN
        assert exception.translation_key == "invalid_filter_lifetime"

    def test_raise_and_catch(self) -> None:
        """Test raising and catching InvalidFilterLifetime."""
        with pytest.raises(InvalidFilterLifetime) as exc_info:
            raise InvalidFilterLifetime()

        assert exc_info.value.translation_domain == DOMAIN
        assert exc_info.value.translation_key == "invalid_filter_lifetime"


class TestInvalidAdaptiveState:
    """Test InvalidAdaptiveState exception."""

    def test_initialization_with_state_only(self) -> None:
        """Test exception initialization with state only."""
        exception = InvalidAdaptiveState("invalid_state")

        assert isinstance(exception, HomeAssistantError)
        assert exception.translation_domain == DOMAIN
        assert exception.translation_key == "invalid_adaptive_state"
        assert exception.translation_placeholders == {"state": "invalid_state"}

    def test_initialization_with_available_states(self) -> None:
        """Test exception initialization with available states."""
        available_states = ["Automatic", "Manual", "Standby", "Boost Mode"]
        exception = InvalidAdaptiveState("invalid_state", available_states)

        assert isinstance(exception, HomeAssistantError)
        assert exception.translation_domain == DOMAIN
        assert exception.translation_key == "invalid_adaptive_state"
        assert (
            exception.translation_placeholders
            == {
                "state": "invalid_state",
                "available_states": "Automatic, Manual, Standby, Boost Mode",  # Simple comma-separated
            }
        )

    def test_inheritance(self) -> None:
        """Test exception inheritance."""
        exception = InvalidAdaptiveState("test")
        assert isinstance(exception, HomeAssistantError)

    def test_raise_and_catch(self) -> None:
        """Test raising and catching InvalidAdaptiveState."""
        with pytest.raises(InvalidAdaptiveState) as exc_info:
            raise InvalidAdaptiveState("bad_state")

        assert exc_info.value.translation_domain == DOMAIN
        assert exc_info.value.translation_key == "invalid_adaptive_state"
        assert exc_info.value.translation_placeholders["state"] == "bad_state"


class TestExceptionBehavior:
    """Test exception behavior in raising and catching."""

    def test_catch_as_home_assistant_error(self) -> None:
        """Test catching InvalidTimeFormat as HomeAssistantError."""
        with pytest.raises(HomeAssistantError) as exc_info:
            raise InvalidTimeFormat()

        assert isinstance(exc_info.value, InvalidTimeFormat)
        assert exc_info.value.translation_domain == DOMAIN
