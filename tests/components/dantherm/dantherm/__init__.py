"""Test proxy for the Dantherm custom integration.

This package exists only for tests so the loader can find the
`custom_components.dantherm` domain. It proxies to the real
implementation located under `config.custom_components.dantherm`.
"""

# Expose DOMAIN for completeness; not strictly required for the tests that
# only exercise the config flow, but harmless and sometimes useful.
DOMAIN = "dantherm"
