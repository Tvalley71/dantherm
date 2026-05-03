"""Root conftest.py - sets up path so that tests can import via 'config.*' and 'tests.*'."""

from __future__ import annotations

import sys
import types
from pathlib import Path

_REPO_ROOT = str(Path(__file__).parent)

# Expose the repo root as the 'config' package so tests can do:
#   from config.custom_components.dantherm.X import Y
if "config" not in sys.modules:
    _config_mod = types.ModuleType("config")
    _config_mod.__path__ = [_REPO_ROOT]
    _config_mod.__package__ = "config"
    sys.modules["config"] = _config_mod

# Expose pytest_homeassistant_custom_component.common as 'tests.common'
# so inner conftest / tests can do: from tests.common import MockConfigEntry
if "tests" not in sys.modules:
    _tests_mod = types.ModuleType("tests")
    _tests_mod.__path__ = [str(Path(__file__).parent / "tests")]
    _tests_mod.__package__ = "tests"
    sys.modules["tests"] = _tests_mod

if "tests.common" not in sys.modules:
    import pytest_homeassistant_custom_component.common as _phcc_common  # noqa: E402

    sys.modules["tests.common"] = _phcc_common
