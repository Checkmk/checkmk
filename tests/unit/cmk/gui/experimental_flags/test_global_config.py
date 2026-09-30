#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.flags import ExperimentalFlagConfig
from cmk.gui import experimental_flags
from cmk.gui.config import Config
from cmk.gui.experimental_flags.global_config import is_development_site
from cmk.gui.global_settings.pages import global_settings
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
)
from tests.testlib.unit.gui.global_settings import patch_factory_defaults, shown_variables

FLAG_NAMES = set(ExperimentalFlagConfig.model_fields)


@pytest.fixture(name="only_experimental_flags_have_defaults")
def fixture_only_experimental_flags_have_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_factory_defaults(monkeypatch, ExperimentalFlagConfig().model_dump())


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


@pytest.mark.usefixtures(
    "only_experimental_flags_have_defaults", "restore_flag_variables", "with_admin_login"
)
def test_a_dev_site_shows_the_experimental_flags(load_config: Config) -> None:
    _register(show_in_global_settings=True)

    assert set(shown_variables(global_settings(load_config))) == FLAG_NAMES


@pytest.mark.usefixtures(
    "only_experimental_flags_have_defaults", "restore_flag_variables", "with_admin_login"
)
def test_a_non_dev_site_hides_the_experimental_flags(load_config: Config) -> None:
    _register(show_in_global_settings=False)

    assert not FLAG_NAMES & set(shown_variables(global_settings(load_config)))


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
