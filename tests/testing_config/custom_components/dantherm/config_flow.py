"""Proxy config_flow for tests to the real implementation.

This module imports the real config flow from the development
integration at `config.custom_components.dantherm.config_flow` so the
test loader can instantiate flows via the `custom_components.dantherm`
namespace.
"""

from config.custom_components.dantherm.config_flow import (  # noqa: F401
    DanthermConfigFlow,
    DanthermOptionsFlowHandler,
)
