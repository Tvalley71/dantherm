"""Translations implementation."""

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


async def async_get_adaptive_state_from_text(
    hass: HomeAssistant, text: str
) -> str | None:
    """Return the matching adaptive state key from translated text."""

    def normalize(s: str) -> str:
        return s.replace("-", "").replace("_", "").replace(" ", "").lower()

    # Get current language
    language = hass.config.language or "en"
    # Fetch translations for the entity domain
    translations = await async_get_translations(hass, language, "entity", [DOMAIN])
    # Build the prefix for adaptive states
    prefix = f"component.{DOMAIN}.entity.sensor.{ATTR_ADAPTIVE_STATE}.state."
    # Filter translations for adaptive states
    adaptive_states = {
        key[len(prefix) :]: localized
        for key, localized in translations.items()
        if key.startswith(prefix)
    }
    # Check if the text matches any localized state or the key itself
    text = normalize(text)
    for key, localized in adaptive_states.items():
        if normalize(localized) == text or normalize(key) == text:
            return key
    return None
