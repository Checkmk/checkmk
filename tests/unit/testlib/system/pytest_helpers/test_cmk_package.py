#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :mod:`tests.testlib.system.pytest_helpers.cmk_package`.

Each test configures a pytest session of its own (``pytester``) with the plugin
loaded. The observable effects are the option values, the environment variables
the rest of tests.testlib reads, and the "Variables" entry of the report metadata.
"""

import os
import re
from collections.abc import Iterator, MutableMapping
from unittest.mock import patch

import pytest
from pytest_metadata.plugin import metadata_key  # type: ignore[import-untyped,unused-ignore]

from tests.testlib.system.pytest_helpers.options import (
    ARG_EDITION_CMK,
    ARG_NO_CLEANUP,
    ARG_REUSE,
    ARG_VERSION_CMK,
    ENV_VAR_CLEANUP,
    ENV_VAR_EDITION,
    ENV_VAR_REUSE,
    ENV_VAR_VERSION,
)

pytest_plugins = ["pytester"]

_PLUGIN = "tests.testlib.system.pytest_helpers.cmk_package"


@pytest.fixture(name="environ")
def fixture_environ() -> Iterator[MutableMapping[str, str]]:
    """The process environment without the plugin's variables, restored after the test."""
    with patch.dict(os.environ):
        for name in (ENV_VAR_EDITION, ENV_VAR_VERSION, ENV_VAR_REUSE, ENV_VAR_CLEANUP, "DISTRO"):
            os.environ.pop(name, None)
        yield os.environ


def _reported_variables(config: pytest.Config) -> list[str]:
    return re.findall(r"<li>\n(.*?)</li>", config.stash[metadata_key]["Variables"])


@pytest.mark.parametrize(
    "env, expected",
    [
        pytest.param({ENV_VAR_REUSE: "1"}, True, id="REUSE=1"),
        pytest.param({ENV_VAR_REUSE: "0"}, False, id="REUSE=0"),
        pytest.param({}, False, id="unset"),
    ],
)
def test_reuse_option_defaults_to_reuse_env_var(
    pytester: pytest.Pytester,
    environ: MutableMapping[str, str],
    env: dict[str, str],
    expected: bool,
) -> None:
    environ.update(env)

    config = pytester.parseconfigure("-p", _PLUGIN)

    assert config.getoption(ARG_REUSE) is expected


@pytest.mark.parametrize(
    "env, expected",
    [
        pytest.param({ENV_VAR_CLEANUP: "0"}, True, id="CLEANUP=0"),
        pytest.param({ENV_VAR_CLEANUP: "1"}, False, id="CLEANUP=1"),
        pytest.param({}, False, id="unset"),
    ],
)
def test_no_cleanup_option_defaults_to_cleanup_env_var(
    pytester: pytest.Pytester,
    environ: MutableMapping[str, str],
    env: dict[str, str],
    expected: bool,
) -> None:
    environ.update(env)

    config = pytester.parseconfigure("-p", _PLUGIN)

    assert config.getoption(ARG_NO_CLEANUP) is expected


@pytest.mark.parametrize(
    "env, expected",
    [
        pytest.param({ENV_VAR_EDITION: "ultimate"}, "ultimate", id="EDITION=ultimate"),
        pytest.param({}, "pro", id="unset"),
    ],
)
def test_cmk_edition_option_defaults_to_edition_env_var(
    pytester: pytest.Pytester,
    environ: MutableMapping[str, str],
    env: dict[str, str],
    expected: str,
) -> None:
    environ.update(env)

    config = pytester.parseconfigure("-p", _PLUGIN)

    assert config.getoption(ARG_EDITION_CMK) == expected


@pytest.mark.parametrize(
    "env, expected",
    [
        pytest.param({ENV_VAR_VERSION: "2.5.0p1"}, "2.5.0p1", id="VERSION=2.5.0p1"),
        pytest.param({}, "daily", id="unset"),
    ],
)
def test_cmk_version_option_defaults_to_version_env_var(
    pytester: pytest.Pytester,
    environ: MutableMapping[str, str],
    env: dict[str, str],
    expected: str,
) -> None:
    environ.update(env)

    config = pytester.parseconfigure("-p", _PLUGIN)

    assert config.getoption(ARG_VERSION_CMK) == expected


@pytest.mark.parametrize(
    "option, env_var, expected",
    [
        pytest.param(ARG_REUSE, ENV_VAR_REUSE, "1", id="reuse"),
        pytest.param(ARG_NO_CLEANUP, ENV_VAR_CLEANUP, "0", id="no-cleanup"),
        pytest.param(f"{ARG_EDITION_CMK}=community", ENV_VAR_EDITION, "community", id="edition"),
        pytest.param(f"{ARG_VERSION_CMK}=2.5.0p1", ENV_VAR_VERSION, "2.5.0p1", id="version"),
    ],
)
def test_command_line_option_overrides_env_var(
    pytester: pytest.Pytester,
    environ: MutableMapping[str, str],
    option: str,
    env_var: str,
    expected: str,
) -> None:
    environ.update(
        {
            ENV_VAR_REUSE: "0",
            ENV_VAR_CLEANUP: "1",
            ENV_VAR_EDITION: "ultimate",
            ENV_VAR_VERSION: "2.4.0p1",
        }
    )

    pytester.parseconfigure("-p", _PLUGIN, option)

    assert environ[env_var] == expected


def test_reuse_option_leaves_cleanup_env_var_unset(
    pytester: pytest.Pytester, environ: MutableMapping[str, str]
) -> None:
    """The site factory keeps a reused site only while CLEANUP is unset."""

    pytester.parseconfigure("-p", _PLUGIN, ARG_REUSE)

    assert ENV_VAR_CLEANUP not in environ


@pytest.mark.usefixtures("environ")
@pytest.mark.parametrize(
    "options, expected",
    [
        pytest.param([], "REUSE=0", id="reuse-default"),
        pytest.param([ARG_REUSE], "REUSE=1", id="reuse"),
        pytest.param([], "CLEANUP=1", id="cleanup-default"),
        pytest.param([ARG_NO_CLEANUP], "CLEANUP=0", id="no-cleanup"),
        pytest.param([], "EDITION=pro", id="edition-default"),
        pytest.param([f"{ARG_EDITION_CMK}=community"], "EDITION=community", id="edition"),
        pytest.param([], "VERSION=daily", id="version-default"),
        pytest.param([f"{ARG_VERSION_CMK}=2.5.0p1"], "VERSION=2.5.0p1", id="version"),
    ],
)
def test_report_lists_values_in_effect(
    pytester: pytest.Pytester, options: list[str], expected: str
) -> None:
    config = pytester.parseconfigure("-p", _PLUGIN, *options)

    assert expected in _reported_variables(config)


def test_report_lists_distro_when_set(
    pytester: pytest.Pytester, environ: MutableMapping[str, str]
) -> None:
    environ["DISTRO"] = "ubuntu-24.04"

    config = pytester.parseconfigure("-p", _PLUGIN)

    assert "DISTRO=ubuntu-24.04" in _reported_variables(config)


@pytest.mark.usefixtures("environ")
def test_report_omits_distro_when_unset(pytester: pytest.Pytester) -> None:
    config = pytester.parseconfigure("-p", _PLUGIN)

    assert [line for line in _reported_variables(config) if line.startswith("DISTRO=")] == []
