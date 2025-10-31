"""Dantherm exceptions."""

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


class InvalidTimeFormat(HomeAssistantError):
    """Raised when a time format is invalid."""

    def __init__(self) -> None:
        """Init HA error."""
        super().__init__(
            translation_domain=DOMAIN, translation_key="invalid_timeformat"
        )


class InvalidFilterLifetime(HomeAssistantError):
    """Raised when filter lifetime is out of valid range."""

    def __init__(self) -> None:
        """Init HA error."""
        super().__init__(
            translation_domain=DOMAIN, translation_key="invalid_filter_lifetime"
        )


class InvalidEntity(HomeAssistantError):
    """Raised when a provided entity ID is not a binary_sensor or input_boolean."""

    def __init__(self) -> None:
        """Init HA error."""
        super().__init__(translation_domain=DOMAIN, translation_key="invalid_entity")


class UnsupportedByFirmware(HomeAssistantError):
    """Raised when an option is not supported on the firmware."""

    def __init__(self) -> None:
        """Init HA error."""
        super().__init__(
            translation_domain=DOMAIN, translation_key="unsupported_by_firmware"
        )


class InvalidAdaptiveState(HomeAssistantError):
    """Raised when an adaptive state is not valid."""

    def __init__(self, state: str, available_states: list[str] | None = None) -> None:
        """Init HA error."""
        placeholders = {"state": state}

        if available_states is not None:
            # Simple comma-separated list - consistent with Home Assistant conventions
            states_list = ", ".join(available_states)
            placeholders["available_states"] = states_list

        super().__init__(
            translation_domain=DOMAIN,
            translation_key="invalid_adaptive_state",
            translation_placeholders=placeholders,
        )
