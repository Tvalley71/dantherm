"""Translations implementation."""

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .device_map import ATTR_ADAPTIVE_STATE


async def async_get_translated_exception_text(
    hass: HomeAssistant, key: str, default=None, message="message"
) -> str:
    """Return a translated exception message."""
    lang = hass.config.language
    translations = await async_get_translations(
        hass, language=lang, category="exceptions", integrations=[DOMAIN]
    )
    full_key = f"component.{DOMAIN}.exceptions.{key}.{message}"

    return translations.get(full_key, default)


async def async_get_translated_state_text(
    hass: HomeAssistant, platform: str, key: str, state
) -> str:
    """Return a translated state text for the current language."""
    lang = hass.config.language
    translations = await async_get_translations(
        hass, language=lang, category="entity", integrations=[DOMAIN]
    )
    full_key = f"component.{DOMAIN}.entity.{platform}.{key}.state.{state}"

    return translations.get(full_key, state)


async def async_get_available_adaptive_states(hass: HomeAssistant) -> dict[str, str]:
    """Return all available adaptive states with their translated names, excluding 'none'."""
    # Get current language
    language = hass.config.language or "en"
    # Fetch translations for the entity domain
    translations = await async_get_translations(hass, language, "entity", [DOMAIN])
    # Build the prefix for adaptive states
    prefix = f"component.{DOMAIN}.entity.sensor.{ATTR_ADAPTIVE_STATE}.state."
    # Filter translations for adaptive states, excluding 'none'
    return {
        key[len(prefix) :]: localized
        for key, localized in translations.items()
        if key.startswith(prefix) and not key.endswith(".none")
    }


async def async_get_adaptive_state_from_summary(
    hass: HomeAssistant, text: str
) -> str | None:
    """Get adaptive state from summary text."""
    # Get all available adaptive states using the existing translation system
    adaptive_states = await async_get_available_adaptive_states(hass)

    if not adaptive_states:
        return None

    def create_precise_pattern(word: str) -> str:
        """Create a regex pattern that matches words precisely, handling _ and - correctly."""
        # Escape special regex characters
        escaped_word = re.escape(word)
        # Use word boundaries, but be more specific about what constitutes a word boundary
        # Allow word boundaries or start/end of string, but not within alphanumeric+underscore sequences
        return rf"(?<!\w){escaped_word}(?!\w)"

    # Look for state in text (precise word matching)
    text_lower = text.lower()

    # Sort by length (longest first) to match more specific terms first
    sorted_states = sorted(
        adaptive_states.items(), key=lambda x: len(x[1]), reverse=True
    )

    for key, translated_value in sorted_states:
        # Check if the translated value appears as a precise word in the text
        pattern = create_precise_pattern(translated_value.lower())
        if re.search(pattern, text_lower):
            return key

        # Also check if the key itself appears as a precise word (for cases like "level_2")
        key_pattern = create_precise_pattern(key.lower())
        if re.search(key_pattern, text_lower):
            return key

    return None
