#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Maps config-variable registration.

Pins the one display group and that every variable maps to the feature's own
config domain.
"""

from cmk.gui.watolib.config_domain_name import (
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)
from cmk.maps.gui import _config_variables
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_LOG_LEVEL,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    CONFIG_VAR_STATE_REFRESH_INTERVAL,
    ConfigDomainMaps,
)


def _register() -> tuple[ConfigVariableGroupRegistry, ConfigVariableRegistry]:
    group_registry = ConfigVariableGroupRegistry()
    variable_registry = ConfigVariableRegistry()
    _config_variables.register(group_registry, variable_registry)
    return group_registry, variable_registry


def test_registers_one_group() -> None:
    group_registry, _vars = _register()
    assert sorted(group_registry.keys()) == ["Maps"]


def test_registers_the_five_variables() -> None:
    _groups, variable_registry = _register()
    assert set(variable_registry) == {
        CONFIG_VAR_CONNECTIONS,
        CONFIG_VAR_LOG_LEVEL,
        CONFIG_VAR_STATE_REFRESH_INTERVAL,
        CONFIG_VAR_MAP_DEFAULTS,
        CONFIG_VAR_OBJECT_DEFAULTS,
    }


def test_all_variables_use_the_feature_domain() -> None:
    # Every Maps setting — daemon-read knobs and the GUI-only authoring defaults
    # alike — lives in the feature's own config domain (like dcd). The daemon just
    # ignores the authoring keys in maps.d.
    _groups, variable_registry = _register()
    for ident in (
        CONFIG_VAR_CONNECTIONS,
        CONFIG_VAR_LOG_LEVEL,
        CONFIG_VAR_STATE_REFRESH_INTERVAL,
        CONFIG_VAR_MAP_DEFAULTS,
        CONFIG_VAR_OBJECT_DEFAULTS,
    ):
        assert variable_registry[ident].primary_domain().ident() == ConfigDomainMaps.ident()
