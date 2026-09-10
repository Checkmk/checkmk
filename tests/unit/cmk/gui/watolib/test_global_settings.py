#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.mkeventd.config_domain import ConfigDomainEventConsole
from cmk.gui.session_context import SuperUserContext
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserInterface
from cmk.gui.watolib.global_settings import affected_sites, is_available_in_global_settings
from cmk.rulesets.v1.form_specs import Integer
from tests.testlib.gui.web_test_app import SetConfig

DEFAULTS = {"test_var": 1}


def _variable(
    domain: type[ABCConfigDomain] = ConfigDomainGUI, *, in_global_settings: bool = True
) -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroupUserInterface,
        primary_domain=domain,
        ident="test_var",
        form_spec=lambda context: Integer(),  # noqa: ARG005
        in_global_settings=in_global_settings,
    )


def _always_activated(varname: str) -> bool:  # noqa: ARG001
    return True


def test_variable_with_a_factory_default_is_available() -> None:
    assert is_available_in_global_settings(
        _variable(), default_values=DEFAULTS, is_activated=_always_activated
    )


def test_variable_without_a_factory_default_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(), default_values={}, is_activated=_always_activated
    )


def test_variable_opting_out_of_the_global_settings_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(in_global_settings=False),
        default_values=DEFAULTS,
        is_activated=_always_activated,
    )


def test_deactivated_variable_is_unavailable() -> None:
    assert not is_available_in_global_settings(
        _variable(),
        default_values=DEFAULTS,
        is_activated=lambda varname: False,  # noqa: ARG005
    )


@pytest.mark.usefixtures("load_config")
def test_variable_of_a_disabled_domain_is_unavailable(set_config: SetConfig) -> None:
    with set_config(mkeventd_enabled=False):
        assert not is_available_in_global_settings(
            _variable(ConfigDomainEventConsole),
            default_values=DEFAULTS,
            is_activated=_always_activated,
        )


@pytest.mark.usefixtures("load_config")
def test_variable_of_a_domain_outside_the_main_page_is_available(set_config: SetConfig) -> None:
    with set_config(mkeventd_enabled=True):
        assert is_available_in_global_settings(
            _variable(ConfigDomainEventConsole),
            default_values=DEFAULTS,
            is_activated=_always_activated,
        )


@pytest.mark.usefixtures("request_context")
def test_affected_sites_of_an_event_console_variable() -> None:
    with SuperUserContext():
        assert affected_sites(config_variable_registry["log_level"]) == ["NO_SITE"]


def test_affected_sites_of_an_ordinary_variable() -> None:
    assert affected_sites(config_variable_registry["wato_max_snapshots"]) is None
