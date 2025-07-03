"""Exceptions."""

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
