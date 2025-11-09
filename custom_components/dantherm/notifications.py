"""Notifications implementation."""

from homeassistant.core import HomeAssistant

from .device_map import CONF_DISABLE_NOTIFICATIONS
from .translations import (
    async_get_translated_exception_text,
    async_get_translated_state_text,
)


async def async_create_key_value_notification(
    hass: HomeAssistant, device_name: str, platform: str, key: str, state: str | None
) -> None:
    """Create a persistent notification."""

    # Get the message and state text for the notification
    message = await async_get_translated_exception_text(hass, f"{key}_notification", "")
    state_str = state or "unknown"
    state_text = await async_get_translated_state_text(hass, platform, key, state_str)

    # Generate a unique notification id based on the device name and key
    notification_id = f"{device_name}_{key}_notification"

    await async_create_notification(
        hass,
        f"{device_name}: {state_text or state_str}",
        message or "",
        notification_id,
    )


async def async_create_exception_notification(
    hass: HomeAssistant,
    device_name: str,
    key: str,
    **placeholders: str | None,
) -> None:
    """Create a persistent notification for an exception."""

    # Get the message for the notification
    message = await async_get_translated_exception_text(hass, f"{key}_notification", "")

    # Clean up placeholders
    clean_placeholders = {k: v for k, v in placeholders.items() if v is not None}
    # Format the message with the cleaned placeholders
    if message:
        message = message.format(**clean_placeholders)
    else:
        message = ""

    # Generate a unique notification id based on the device name and key
    notification_id = f"{device_name}_{key}_notification"

    await async_create_notification(hass, f"{device_name}", message, notification_id)


async def async_create_notification(
    hass: HomeAssistant,
    title: str,
    message: str = "",
    notification_id: str | None = None,
) -> None:
    """Create a persistent notification in Home Assistant."""

    if message != "":
        message += "\n\n"
    disable_text = await async_get_translated_exception_text(
        hass, CONF_DISABLE_NOTIFICATIONS
    )
    if disable_text:
        message += disable_text

    data = {
        "title": title,
        "message": message,
    }
    if notification_id:
        data["notification_id"] = notification_id

    hass.async_create_task(
        hass.services.async_call(
            "persistent_notification",
            "create",
            data,
        )
    )


async def async_dismiss_notification(
    hass: HomeAssistant, device_name: str, key: str
) -> None:
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
