"""Support utilities for Dantherm integration."""

import base64
import contextlib
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Patterns for sanitizing sensitive data in logs
SENSITIVE_PATTERNS = [
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "**IP_REDACTED**"),  # IP addresses
    (
        r"\b[A-Fa-f0-9]{2}(?:[:-][A-Fa-f0-9]{2}){5}\b",
        "**MAC_REDACTED**",
    ),  # MAC addresses
    (r"\b[A-Za-z0-9+/]{20,}\b", "**TOKEN_REDACTED**"),  # Long tokens/keys
    (r"\b\w+@\w+\.\w+\b", "**EMAIL_REDACTED**"),  # Email addresses
    (
        r"\bserial[_\s]*number[_\s]*[:=]\s*\S+",
        "serial_number: **REDACTED**",
    ),  # Serial numbers
    (r"\bpassword[_\s]*[:=]\s*\S+", "password: **REDACTED**"),  # Passwords
    (r"\bapi[_\s]*key[_\s]*[:=]\s*\S+", "api_key: **REDACTED**"),  # API keys
    (r"\bauth[_\s]*token[_\s]*[:=]\s*\S+", "auth_token: **REDACTED**"),  # Auth tokens
]


def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages."""
    sanitized = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


async def async_toggle_debug_logging(hass: HomeAssistant, enable: bool = True) -> bool:
    """Programmatically enable/disable debug logging for this integration."""
    try:
        integration_logger = f"custom_components.{DOMAIN}"

        if enable:
            # Enable debug logging
            logger = logging.getLogger(integration_logger)
            logger.setLevel(logging.DEBUG)

            # Update Home Assistant's logger service if available
            with contextlib.suppress(Exception):
                await hass.services.async_call(
                    "logger",
                    "set_level",
                    {integration_logger: "debug"},
                    blocking=True,
                )
        else:
            # Disable debug logging (reset to default)
            with contextlib.suppress(Exception):
                await hass.services.async_call(
                    "logger",
                    "set_level",
                    {integration_logger: "notset"},
                    blocking=True,
                )
            # Fallback to direct logger setting
            logger = logging.getLogger(integration_logger)
            logger.setLevel(logging.NOTSET)
        return True
    except (AttributeError, ValueError, RuntimeError) as ex:
        _LOGGER.error("Failed to toggle debug logging: %s", ex)
        return False


async def async_collect_integration_logs(
    hass: HomeAssistant, hours: int = 24, max_entries: int = 100
) -> dict[str, Any]:
    """Collect and sanitize integration-specific logs."""

    logs_data = {
        "total_entries": 0,
        "entries_by_level": {},
        "entries": [],
        "collection_info": {
            "hours_covered": hours,
            "max_entries": max_entries,
            "sanitized": True,
            "collection_time": datetime.now().isoformat(),
        },
    }

    try:
        # Get integration logger
        integration_logger = logging.getLogger(f"custom_components.{DOMAIN}")
        current_level = integration_logger.getEffectiveLevel()
        debug_enabled = integration_logger.isEnabledFor(logging.DEBUG)

        logs_data["collection_info"].update(
            {
                "current_log_level": logging.getLevelName(current_level),
                "debug_enabled": debug_enabled,
            }
        )

        # Try to collect recent logs from memory handlers
        await _collect_from_memory_handlers(logs_data, hours, max_entries)

        # Add some diagnostic logging entries
        await _generate_diagnostic_logs(hass, logs_data)

    except (RuntimeError, ValueError, AttributeError) as ex:
        _LOGGER.error("Error collecting integration logs: %s", ex)
        logs_data["collection_info"]["error"] = (
            f"Collection failed: {type(ex).__name__}"
        )

    return logs_data


async def _collect_from_memory_handlers(
    logs_data: dict[str, Any], hours: int, max_entries: int
) -> None:
    """Try to collect logs from memory handlers."""
    try:
        root_logger = logging.getLogger()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        collected_entries = []

        # Look for handlers that might store log records
        for handler in root_logger.handlers:
            if hasattr(handler, "buffer") and handler.buffer:
                for record in handler.buffer:
                    if len(collected_entries) >= max_entries:
                        break

                    # Only include records from our integration
                    if (
                        record.name.startswith(f"custom_components.{DOMAIN}")
                        and datetime.fromtimestamp(record.created) > cutoff_time
                    ):
                        try:
                            entry = {
                                "timestamp": datetime.fromtimestamp(
                                    record.created
                                ).isoformat(),
                                "level": record.levelname,
                                "logger": record.name.replace(
                                    f"custom_components.{DOMAIN}.", ""
                                ),
                                "message": sanitize_log_message(record.getMessage()),
                                "module": getattr(record, "module", None),
                                "function": getattr(record, "funcName", None),
                                "line": getattr(record, "lineno", None),
                                "source": "memory_buffer",
                            }

                            # Add exception info if present
                            if record.exc_info and record.exc_info[1]:
                                entry["exception"] = sanitize_log_message(
                                    str(record.exc_info[1])
                                )

                            collected_entries.append(entry)
                        except (AttributeError, ValueError, TypeError):
                            # Skip problematic records
                            continue

        # Update logs data
        logs_data["entries"].extend(collected_entries)
        logs_data["total_entries"] = len(logs_data["entries"])

        # Count by level
        level_counts = {}
        for entry in logs_data["entries"]:
            level = entry.get("level", "UNKNOWN")
            level_counts[level] = level_counts.get(level, 0) + 1
        logs_data["entries_by_level"] = level_counts

    except (RuntimeError, ValueError, AttributeError) as ex:
        _LOGGER.debug("Could not collect from memory handlers: %s", ex)


async def _generate_diagnostic_logs(
    hass: HomeAssistant, logs_data: dict[str, Any]
) -> None:
    """Generate some diagnostic log entries for testing."""
    try:
        diagnostic_entries = []

        # Log current integration status
        domain_data = hass.data.get(DOMAIN, {})
        entry_count = len([k for k in domain_data if isinstance(k, str)])

        diagnostic_entries.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "logger": "support",
                "message": f"Integration has {entry_count} active config entries",
                "source": "diagnostic_collection",
            }
        )

        # Log memory usage info (sanitized)
        try:
            memory_info = sys.getsizeof(domain_data)
            diagnostic_entries.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "DEBUG",
                    "logger": "support",
                    "message": f"Integration data memory usage: {memory_info} bytes",
                    "source": "diagnostic_collection",
                }
            )
        except (AttributeError, ValueError):
            pass

        # Add diagnostic entries to logs
        logs_data["entries"].extend(diagnostic_entries)
        logs_data["total_entries"] = len(logs_data["entries"])

        # Update level counts
        for entry in diagnostic_entries:
            level = entry.get("level", "UNKNOWN")
            logs_data["entries_by_level"][level] = (
                logs_data["entries_by_level"].get(level, 0) + 1
            )

    except (RuntimeError, ValueError, AttributeError) as ex:
        _LOGGER.debug("Error generating diagnostic logs: %s", ex)


async def create_download_service_response(hass: HomeAssistant) -> dict[str, Any]:
    """Create a service response with downloadable log data."""
    try:
        # Collect fresh logs
        logs_data = await async_collect_integration_logs(
            hass, hours=24, max_entries=100
        )

        # Prepare download data
        download_data = {
            "integration": DOMAIN,
            "collection_timestamp": datetime.now().isoformat(),
            "home_assistant_version": hass.config.version,
            "logs": logs_data,
        }

        # Convert to JSON string
        json_content = json.dumps(download_data, indent=2, ensure_ascii=False)

        # Create data URL for download
        json_bytes = json_content.encode("utf-8")
        b64_content = base64.b64encode(json_bytes).decode("ascii")
        data_url = f"data:application/json;charset=utf-8;base64,{b64_content}"

        filename = f"dantherm_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return {
            "success": True,
            "filename": filename,
            "data_url": data_url,
            "size_kb": round(len(json_content) / 1024, 1),
            "entries": logs_data.get("total_entries", 0),
            "message": f"Log file '{filename}' ready for download ({round(len(json_content) / 1024, 1)} KB)",
        }

    except (RuntimeError, ValueError, AttributeError, TypeError) as ex:
        return {
            "success": False,
            "error": f"Failed to create download: {type(ex).__name__}: {ex}",
            "message": "Failed to generate log download",
        }


def get_logging_instructions() -> dict[str, Any]:
    """Provide instructions for users to gather additional logs safely."""
    return {
        "instructions": {
            "enable_debug": f"To enable debug logging for this integration only, add this to your configuration.yaml:\n\nlogger:\n  logs:\n    custom_components.{DOMAIN}: debug",
            "view_logs": f"After enabling debug logging, restart Home Assistant and reproduce the issue. Then use Developer Tools > Download Diagnostics or check logs for entries containing '{DOMAIN}'",
            "sensitive_data_warning": "Integration logs are automatically sanitized to remove IP addresses, MAC addresses, and tokens. However, please review before sharing publicly.",
            "log_location": "Full logs are available in the Home Assistant log file, typically at config/home-assistant.log",
        },
        "current_log_level": logging.getLogger(
            f"custom_components.{DOMAIN}"
        ).getEffectiveLevel(),
        "debug_enabled": logging.getLogger(f"custom_components.{DOMAIN}").isEnabledFor(
            logging.DEBUG
        ),
    }


async def async_create_downloadable_support_file(
    hass: HomeAssistant,
    entry_id: str,
    entry_title: str,
    *,
    prefix: str = "dantherm_support",
) -> dict[str, str]:
    """Create and write a JSON support file under config/www and return URLs."""

    # Collect logs
    logs_data = await async_collect_integration_logs(hass)

    # Build data to persist
    ts = datetime.now()
    timestamp = ts.strftime("%Y%m%d_%H%M%S")
    download_data = {
        "integration": DOMAIN,
        "collection_timestamp": ts.isoformat(),
        "home_assistant_version": hass.config.version,
        "config_entry_title": entry_title,
        "logs": logs_data,
    }

    filename = f"{prefix}_{timestamp}.json"
    file_path = Path(hass.config.path("www", filename))
    file_path.parent.mkdir(exist_ok=True)

    def write_file() -> None:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(download_data, f, indent=2, ensure_ascii=False)

    await hass.async_add_executor_job(write_file)

    return {
        "filename": filename,
        "file_path": str(file_path),
        "local_url": f"/local/{filename}",
        "forced_download_url": f"/api/{DOMAIN}/{entry_id}/download/{filename}",
        "timestamp": timestamp,
    }


class DanthermLogDownloadView(HomeAssistantView):
    """Serve generated support/log files as attachments for download."""

    url = f"/api/{DOMAIN}/{{entry_id}}/download/{{filename}}"
    name = "api:dantherm:download"
    # Files in /www are already publicly exposed via /local
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the download view with hass reference."""
        self.hass = hass

    async def get(self, request, entry_id: str, filename: str):  # type: ignore[override]
        """Handle GET requests and return the file as an attachment.

        Parameters:
            request: The aiohttp request.
            entry_id: The config entry id (not used for file lookup, kept for URL shape).
            filename: The expected filename under config/www to serve.
        """
        # Restrict to JSON files we generate for this integration
        if not (filename.startswith("dantherm_") and filename.endswith(".json")):
            return web.Response(status=404)

        www_dir = self.hass.config.path("www")
        base = Path(www_dir).resolve()
        target = Path(self.hass.config.path("www", filename)).resolve()

        # Prevent path traversal
        if not str(target).startswith(str(base)):
            return web.Response(status=403)

        try:
            data = target.read_bytes()
        except FileNotFoundError:
            return web.Response(status=404)

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return web.Response(
            body=data, headers=headers, content_type="application/octet-stream"
        )
