"""Tests for notifications helper functions."""

from unittest.mock import AsyncMock, patch

from config.custom_components.dantherm import notifications as dn
import pytest

from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_async_create_notification_with_message(hass: HomeAssistant) -> None:
    """It should append the footer and include notification_id when provided."""

    # Patch translation footer text
    with (
        patch(
            "config.custom_components.dantherm.notifications.async_get_translated_exception_text",
            new=AsyncMock(return_value="footer"),
        ) as mock_footer,
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new=AsyncMock()
        ) as mock_call,
    ):
        await dn.async_create_notification(
            hass, title="Title", message="Body", notification_id="nid"
        )

        mock_footer.assert_awaited_once()
        # Validate the last two args: service and data (domain may not be present on this bound mock)
        args = mock_call.await_args.args
        assert args[-2:] == (
            "create",
            {
                "title": "Title",
                "message": "Body\n\nfooter",
                "notification_id": "nid",
            },
        )


@pytest.mark.asyncio
async def test_async_create_notification_without_message(hass: HomeAssistant) -> None:
    """It should send only the footer when message is empty."""

    with (
        patch(
            "config.custom_components.dantherm.notifications.async_get_translated_exception_text",
            new=AsyncMock(return_value="footer"),
        ) as mock_footer,
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new=AsyncMock()
        ) as mock_call,
    ):
        await dn.async_create_notification(hass, title="OnlyFooter")

        mock_footer.assert_awaited_once()
        args = mock_call.await_args.args
        assert args[-2:] == (
            "create",
            {"title": "OnlyFooter", "message": "footer"},
        )


@pytest.mark.asyncio
async def test_async_create_key_value_notification(hass: HomeAssistant) -> None:
    """It should translate and delegate to async_create_notification with expected args."""

    with (
        patch(
            "config.custom_components.dantherm.notifications.async_get_translated_exception_text",
            new=AsyncMock(return_value="header"),
        ) as mock_exc_text,
        patch(
            "config.custom_components.dantherm.notifications.async_get_translated_state_text",
            new=AsyncMock(return_value="TranslatedState"),
        ) as mock_state_text,
        patch(
            "config.custom_components.dantherm.notifications.async_create_notification",
            new=AsyncMock(),
        ) as mock_create,
    ):
        await dn.async_create_key_value_notification(
            hass, device_name="Dev", platform="sensor", key="alarm", state=5
        )

        mock_exc_text.assert_awaited_once()
        mock_state_text.assert_awaited_once()
        # Validate the delegated call arguments
        args, kwargs = mock_create.await_args
        assert args[0] is hass
        assert kwargs == {}
        assert args[1] == "Dev: TranslatedState"
        assert args[2] == "header"
        assert args[3] == "Dev_alarm_notification"


@pytest.mark.asyncio
async def test_async_create_exception_notification(hass: HomeAssistant) -> None:
    """It should create title from device only and format placeholders in message template."""

    with (
        patch(
            "config.custom_components.dantherm.notifications.async_get_translated_exception_text",
            new=AsyncMock(return_value="Error: code={code}"),
        ) as mock_exc_text,
        patch(
            "config.custom_components.dantherm.notifications.async_create_notification",
            new=AsyncMock(),
        ) as mock_create,
    ):
        await dn.async_create_exception_notification(
            hass, device_name="Dev", key="network", code="E42", ignore=None
        )

        mock_exc_text.assert_awaited_once()
        args, kwargs = mock_create.await_args
        assert args[0] is hass
        assert kwargs == {}
        assert args[1] == "Dev"
        assert args[2] == "Error: code=E42"
        assert args[3] == "Dev_network_notification"


@pytest.mark.asyncio
async def test_async_dismiss_notification(hass: HomeAssistant) -> None:
    """It should call persistent_notification.dismiss with expected id."""

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new=AsyncMock()
    ) as mock_call:
        await dn.async_dismiss_notification(hass, device_name="Dev", key="alarm")

        args = mock_call.await_args.args
        assert args[-2:] == (
            "dismiss",
            {"notification_id": "Dev_alarm_notification"},
        )
