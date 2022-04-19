#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.checkmk_agent import (
    _check_agent_update,
    _check_cmk_agent_update,
    _check_only_from,
    _check_python_plugins,
    _check_transport,
    _check_version,
    check_checkmk_agent,
    discover_checkmk_agent,
)
from cmk.base.plugins.agent_based.utils.checkmk import ControllerSection, Plugin, PluginSection

# TODO: make this more blackboxy once API vialoations are reduced!


def test_discovery_something() -> None:
    assert [*discover_checkmk_agent({}, None, None)] == [Service()]


def test_check_no_data() -> None:
    assert not [*check_checkmk_agent({}, None, None, None)]


def test_check_version_os_no_values() -> None:
    assert not [
        *_check_version(
            None,
            "site_version",
            ("specific", {"literal": "irrelevant"}),
            State.WARN,
        )
    ]


def test_check_version_os_no_params() -> None:
    assert [
        *_check_version(
            "1.2.3",
            "site_version",
            ("ignore", {}),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


def test_check_version_match() -> None:
    assert [
        *_check_version(
            "1.2.3",
            "2.1.0",
            ("specific", {"literal": "1.2.3"}),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_version_mismatch(fail_state: State) -> None:
    assert [*_check_version("1.2.3", "1.2.3", ("specific", {"literal": "1.2.2"}), fail_state,)] == [
        Result(state=fail_state, summary="Version: 1.2.3 (expected 1.2.2)"),
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_version_site_mismatch(fail_state: State) -> None:
    assert [*_check_version("1.2.3", "1.2.2", ("site", {}), fail_state,)] == [
        Result(state=fail_state, summary="Version: 1.2.3 (expected 1.2.2)"),
    ]


def test_check_version_at_least_success():
    assert [
        *_check_version(
            "1.2.3",
            "site.version",
            ("at_least", {"release": "1.1.0"}),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


def test_check_version_at_least_dict_empty():
    spec: dict[str, str] = {}
    assert [
        *_check_version(
            "1.2.3",
            "site.version",
            ("at_least", spec),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


def test_check_version_at_least_daily_build():
    assert [
        *_check_version(
            "1.2.3-2021.02.03",
            "site.version",
            ("at_least", {"daily_build": "2022.03.04"}),
            State.WARN,
        )
    ] == [
        Result(
            state=State.WARN,
            summary="Version: 1.2.3-2021.02.03 (expected at least 2022.03.04)",
        )
    ]


def test_check_version_at_least_daily_build_vs_release():
    assert [
        *_check_version(
            "1.2.3-2022.02.03",
            "site.version",
            ("at_least", {"release": "1.2.3"}),
            State.WARN,
        )
    ] == [
        Result(
            state=State.WARN,
            summary="Version: 1.2.3-2022.02.03 (expected at least 1.2.3)",
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_only_from(fail_state: State) -> None:
    assert [
        *_check_only_from(
            "1.2.3.4 5.6.7.8",
            "1.2.3.4",
            fail_state,
        )
    ] == [Result(state=fail_state, summary="Unexpected allowed IP ranges (exceeding: 5.6.7.8)")]


def test_check_agent_update_failed_not() -> None:
    assert not [*_check_agent_update("what", None)]


def test_check_agent_update_failed() -> None:
    assert [*_check_agent_update("what", "why")] == [Result(state=State.WARN, summary="what why")]


def test_check_faild_python_plugins_ok() -> None:
    assert not [
        *_check_python_plugins(
            None,
            "I'm not in the mood to execute python plugins",
        )
    ]


def test_check_faild_python_plugins() -> None:
    assert [
        *_check_python_plugins(
            "one two",
            "I'm not in the mood to execute python plugins",
        )
    ] == [
        Result(
            state=State.WARN,
            summary=(
                "Failed to execute python plugins: one two"
                " (I'm not in the mood to execute python plugins)"
            ),
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_ls_ok(fail_state: State) -> None:
    assert not [
        *_check_transport(
            False,
            ControllerSection(allow_legacy_pull=False, ip_allowlist=()),
            fail_state,
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_no_tls(fail_state: State) -> None:
    assert [
        *_check_transport(
            False,
            ControllerSection(allow_legacy_pull=True, ip_allowlist=()),
            fail_state,
        )
    ] == [
        Result(
            state=fail_state,
            summary="TLS is not activated on monitored host (see details)",
            details=(
                "The hosts agent supports TLS, but it is not being used. "
                "We strongly recommend to enable TLS by registering the host to the site"
                " (using the `cmk-agent-ctl register` command on the monitored host). "
                "However you can configure missing TLS to be OK in the setting"
                ' "State in case of available but not enabled TLS" of the ruleset'
                ' "Status of the Checkmk services".'
            ),
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_no_controller(fail_state: State) -> None:
    assert not [*_check_transport(False, None, fail_state)]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_via_ssh(fail_state: State) -> None:
    assert [*_check_transport(True, None, fail_state)] == [
        Result(state=State.OK, summary="Transport via SSH")
    ]


def test_check_no_check_yet() -> None:
    assert [*_check_cmk_agent_update({}, {"agentupdate": "last_check None error None"})] == [
        Result(state=State.WARN, summary="No successful connect to server yet"),
    ]


@pytest.mark.parametrize("duplicate", [False, True])
def test_check_warn_upon_old_update_check(duplicate: bool) -> None:
    with on_time(1645800081.5039608, "UTC"):
        actual = list(
            _check_cmk_agent_update(
                {},
                {
                    "agentupdate": " ".join(
                        (1 + duplicate)
                        * (
                            "last_check 1645000081.5039608",
                            "last_update 1645000181.5039608",
                            "aghash 38bf6e44175732bc",
                            "pending_hash 1234abcd5678efgh",
                            "update_url https://server/site/check_mk",
                            "error 503 Server Error: Service Unavailable",
                        )
                    )
                },
            )
        )

    assert actual == [
        Result(state=State.WARN, summary="Update error: 503 Server Error: Service Unavailable"),
        Result(
            state=State.WARN,
            summary="Time since last update check: 9 days 6 hours (warn/crit at 2 days 0 hours/never)",
        ),
        Result(state=State.OK, notice="Last update check: Feb 16 2022 08:28:01"),
        Result(state=State.OK, summary="Last update: Feb 16 2022 08:29:41"),
        Result(state=State.OK, notice="Update URL: https://server/site/check_mk"),
        Result(state=State.OK, notice="Agent configuration: 38bf6e44"),
        Result(state=State.OK, notice="Pending installation: 1234abcd"),
    ]


@pytest.mark.parametrize(
    [
        "params",
        "section_plugins",
        "expected_result",
    ],
    [
        pytest.param(
            {},
            None,
            [],
            id="no data",
        ),
        pytest.param(
            {},
            PluginSection(
                plugins=[
                    Plugin(
                        name="plugin1",
                        version="2.1.0i1",
                        version_int=2010010100,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="plugin2",
                        version="2.0.0p20",
                        version_int=2000050020,
                        cache_interval=None,
                    ),
                ],
                local_checks=[],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 2",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 0",
                ),
            ],
            id="agent plugins only",
        ),
        pytest.param(
            {},
            PluginSection(
                plugins=[],
                local_checks=[
                    Plugin(
                        name="check1.sh",
                        version="1.3.45",
                        version_int=1345000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="1.0",
                        version_int=1000000000,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 0",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 2",
                ),
            ],
            id="local checks only",
        ),
        pytest.param(
            {
                "versions_plugins": {
                    "min_versions": (
                        "2.0.0p21",
                        "2.0.0p15",
                    ),
                    "mon_state_unparsable": 3,
                },
                "versions_lchecks": {
                    "min_versions": (
                        "1.2",
                        "1.1",
                    ),
                    "mon_state_unparsable": 1,
                },
            },
            PluginSection(
                plugins=[
                    Plugin(
                        name="plugin1",
                        version="2.1.0i1",
                        version_int=2010010100,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="plugin2",
                        version="2.0.0p20",
                        version_int=2000050020,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="custom_plugin3",
                        version="??",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
                local_checks=[
                    Plugin(
                        name="check1.sh",
                        version="1.3.45",
                        version_int=1345000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="1.0",
                        version_int=1000000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check3.py",
                        version="[fill in later]",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 3",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 3",
                ),
                Result(
                    state=State.OK,
                    notice="Agent plugin 'plugin1': 2.1.0i1",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plugin 'plugin2': 2.0.0p20 (warn/crit below 2.0.0p21/2.0.0p15)",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="Agent plugin 'custom_plugin3': unable to parse version '??'",
                ),
                Result(
                    state=State.OK,
                    notice="Local check 'check1.sh': 1.3.45",
                ),
                Result(
                    state=State.CRIT,
                    summary="Local check 'check2.py': 1.0 (warn/crit below 1.2/1.1)",
                ),
                Result(
                    state=State.WARN,
                    summary="Local check 'check3.py': unable to parse version '[fill in later]'",
                ),
            ],
            id="version checks",
        ),
        pytest.param(
            {
                "versions_plugins": {
                    "min_versions": (
                        "2.0.0p21",
                        "2.0.0p15",
                    ),
                    "mon_state_unparsable": 3,
                },
                "exclude_pattern_plugins": "custom.*",
                "versions_lchecks": {
                    "min_versions": (
                        "1.2",
                        "1.1",
                    ),
                    "mon_state_unparsable": 1,
                },
                "exclude_pattern_lchecks": r"check3\.py",
            },
            PluginSection(
                plugins=[
                    Plugin(
                        name="plugin1",
                        version="2.1.0i1",
                        version_int=2010010100,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="plugin2",
                        version="2.0.0p20",
                        version_int=2000050020,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="custom_plugin3",
                        version="??",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
                local_checks=[
                    Plugin(
                        name="check1.sh",
                        version="1.3.45",
                        version_int=1345000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="1.0",
                        version_int=1000000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check3.py",
                        version="[fill in later]",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 3",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 3",
                ),
                Result(
                    state=State.OK,
                    notice="Agent plugin 'plugin1': 2.1.0i1",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plugin 'plugin2': 2.0.0p20 (warn/crit below 2.0.0p21/2.0.0p15)",
                ),
                Result(
                    state=State.OK,
                    notice="Local check 'check1.sh': 1.3.45",
                ),
                Result(
                    state=State.CRIT,
                    summary="Local check 'check2.py': 1.0 (warn/crit below 1.2/1.1)",
                ),
            ],
            id="version checks with excludes",
        ),
        pytest.param(
            {},
            PluginSection(
                plugins=[
                    Plugin(
                        name="plugin1",
                        version="2.1.0i1",
                        version_int=2010010100,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="plugin1",
                        version="2.0.0p20",
                        version_int=2000050020,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="custom_plugin3",
                        version="??",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
                local_checks=[
                    Plugin(
                        name="check1.sh",
                        version="1.3.45",
                        version_int=1345000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="1.0",
                        version_int=1000000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="[fill in later]",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 3",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 3",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plugin plugin1: found 2 times",
                    details="Consult the hardware/software inventory for a complete list of files",
                ),
                Result(
                    state=State.WARN,
                    summary="Local check check2.py: found 2 times",
                    details="Consult the hardware/software inventory for a complete list of files",
                ),
            ],
            id="duplicate files",
        ),
        pytest.param(
            {
                "exclude_pattern_plugins": "custom.*",
                "exclude_pattern_lchecks": ".*py",
            },
            PluginSection(
                plugins=[
                    Plugin(
                        name="plugin1",
                        version="2.1.0i1",
                        version_int=2010010100,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="plugin1",
                        version="2.0.0p20",
                        version_int=2000050020,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="custom_plugin3",
                        version="??",
                        version_int=None,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="custom_plugin3",
                        version="???",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
                local_checks=[
                    Plugin(
                        name="check1.sh",
                        version="1.3.45",
                        version_int=1345000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="1.0",
                        version_int=1000000000,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check2.py",
                        version="[fill in later]",
                        version_int=None,
                        cache_interval=None,
                    ),
                    Plugin(
                        name="check1.sh",
                        version="1.2.45",
                        version_int=1245000000,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plugins: 4",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 4",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plugin plugin1: found 2 times",
                    details="Consult the hardware/software inventory for a complete list of files",
                ),
                Result(
                    state=State.WARN,
                    summary="Local check check1.sh: found 2 times",
                    details="Consult the hardware/software inventory for a complete list of files",
                ),
            ],
            id="duplicate files with excludes",
        ),
    ],
)
def test_check_plugins(
    params: Mapping[str, Any],
    section_plugins: Optional[PluginSection],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_checkmk_agent(
                params,
                None,
                section_plugins,
                None,
            )
        )
        == expected_result
    )
