#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.flags import ExperimentalFlagConfig
from cmk.gui import experimental_flags
from cmk.gui.experimental_flags.global_config import is_development_site
from cmk.gui.wato.pages.global_settings import DefaultModeEditGlobals
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
)

FLAG_NAMES = set(ExperimentalFlagConfig.model_fields)


@pytest.fixture(name="no_factory_defaults")
def fixture_no_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real lookup runs an automation that needs a site.
    monkeypatch.setattr(ABCConfigDomain, "get_all_default_globals", lambda: {})


@pytest.fixture(name="restore_flag_variables")
def fixture_restore_flag_variables() -> Iterator[None]:
    registered = [config_variable_registry[name] for name in FLAG_NAMES]
    yield
    for config_variable in registered:
        config_variable_registry.register(config_variable)


def _register(*, show_in_global_settings: bool) -> None:
    experimental_flags.register(
        config_domain_registry,
        config_variable_registry,
        config_variable_group_registry,
        show_in_global_settings=show_in_global_settings,
    )


def _shown_variables() -> set[str]:
    return {
        config_variable.ident()
        for _group, config_variables in DefaultModeEditGlobals().iter_all_configuration_variables(
            debug=False
        )
        for config_variable in config_variables
    }


@pytest.mark.usefixtures("no_factory_defaults", "restore_flag_variables", "request_context")
def test_a_dev_site_shows_the_experimental_flags() -> None:
    _register(show_in_global_settings=True)

    assert FLAG_NAMES <= _shown_variables()


@pytest.mark.usefixtures("no_factory_defaults", "restore_flag_variables", "request_context")
def test_a_non_dev_site_hides_the_experimental_flags() -> None:
    _register(show_in_global_settings=False)

    assert not FLAG_NAMES & _shown_variables()


@pytest.mark.parametrize(
    "environ, expected",
    [
        pytest.param({"CMK_DEV": "True"}, True, id="set"),
        pytest.param({"CMK_DEV": "true"}, True, id="lowercase"),
        pytest.param({"CMK_DEV": "False"}, False, id="false"),
        pytest.param({}, False, id="unset"),
    ],
)
def test_is_development_site(environ: dict[str, str], expected: bool) -> None:
    assert is_development_site(environ) is expected
