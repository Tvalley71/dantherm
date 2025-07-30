"""Notifications implementation."""

from homeassistant.core import HomeAssistant

from .device_map import ATTR_DISABLE_NOTIFICATIONS
from .translations import (
    async_get_translated_exception_text,
    async_get_translated_state_text,
)


async def async_create_notification(
    hass: HomeAssistant, device_name: str, platform: str, key: str, state
):
    """Create a persistent notification."""

    # Get the message and state text for the notification
    message = await async_get_translated_exception_text(hass, f"{key}_notification", "")
    if message != "":
        message += "\n\n"
    message += await async_get_translated_exception_text(
        hass, ATTR_DISABLE_NOTIFICATIONS
    )
    state_text = await async_get_translated_state_text(hass, platform, key, state)

    # Generate a unique notification id based on the device name and key
    notification_id = f"{device_name}_{key}_notification"

    # Create a persistent notification in Home Assistant
    hass.async_create_task(
        hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": f"{device_name}: {state_text}",
                "message": f"{message}",
                "notification_id": f"{notification_id}",
            },
        )
    )


async def async_dismiss_notification(hass: HomeAssistant, device_name: str, key: str):
    """Dismiss a persistent notification."""

    # Generate the notification id based on the device name and key
    notification_id = f"{device_name}_{key}_notification"

    # Dismiss the persistent notification in Home Assistant
    hass.async_create_task(
        hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": notification_id},
        )
    )
