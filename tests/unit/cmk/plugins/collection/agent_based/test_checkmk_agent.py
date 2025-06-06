#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, UTC
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.collection.agent_based.checkmk_agent import (
    _check_agent_update,
    _check_cmk_agent_update,
    _check_encryption_panic,
    _check_only_from,
    _check_python_plugins,
    _check_transport,
    _check_version,
    _get_error_result,
    check_checkmk_agent,
    discover_checkmk_agent,
)
from cmk.plugins.collection.agent_based.checkmk_agent import (
    _expand_curly_address_notation as expand_curly_address_notation,
)
from cmk.plugins.collection.agent_based.cmk_update_agent_status import (
    _parse_cmk_update_agent_status,
)
from cmk.plugins.lib.checkmk import (
    CachedPlugin,
    CachedPluginsSection,
    CachedPluginType,
    CertInfoController,
    CMKAgentUpdateSection,
    Connection,
    ControllerSection,
    LocalConnectionStatus,
    Plugin,
    PluginSection,
)

# TODO: make this more blackboxy once API vialoations are reduced!


def test_discovery_something() -> None:
    assert [*discover_checkmk_agent({}, None, None, None, None)] == [Service()]


def test_check_no_data() -> None:
    assert not [*check_checkmk_agent({}, None, None, None, None, None)]


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
    assert [
        *_check_version(
            "1.2.3",
            "1.2.3",
            ("specific", {"literal": "1.2.2"}),
            fail_state,
        )
    ] == [
        Result(state=fail_state, summary="Version: 1.2.3 (expected 1.2.2)"),
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_version_site_mismatch(fail_state: State) -> None:
    assert [
        *_check_version(
            "1.2.3",
            "1.2.2",
            ("site", {}),
            fail_state,
        )
    ] == [
        Result(state=fail_state, summary="Version: 1.2.3 (expected 1.2.2)"),
    ]


def test_check_version_at_least_success() -> None:
    assert [
        *_check_version(
            "1.2.3",
            "site.version",
            ("at_least", {"release": "1.1.0"}),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


def test_check_version_at_least_dict_empty() -> None:
    spec: dict[str, str] = {}
    assert [
        *_check_version(
            "1.2.3",
            "site.version",
            ("at_least", spec),
            State.WARN,
        )
    ] == [Result(state=State.OK, summary="Version: 1.2.3")]


def test_check_version_at_least_daily_build() -> None:
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


def test_check_version_at_least_daily_build_vs_release() -> None:
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


def test_check_encryption_panic() -> None:
    assert [*_check_encryption_panic("something")] == [
        Result(
            state=State.CRIT,
            summary="Failed to apply symmetric encryption, aborting communication.",
        )
    ]


def test_check_no_encryption_panic() -> None:
    assert not [*_check_encryption_panic(None)]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_ls_ok(fail_state: State) -> None:
    assert not [
        *_check_transport(
            False,
            ControllerSection(
                allow_legacy_pull=False,
                ip_allowlist=[],
                agent_socket_operational=True,
                connections=[],
            ),
            fail_state,
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_no_tls_controller_not_in_use(fail_state: State) -> None:
    assert not [
        *_check_transport(
            False,
            ControllerSection(
                allow_legacy_pull=True,
                ip_allowlist=[],
                agent_socket_operational=False,
                connections=[],
            ),
            fail_state,
        )
    ]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_no_tls(fail_state: State) -> None:
    (result,) = _check_transport(
        False,
        ControllerSection(
            allow_legacy_pull=True,
            ip_allowlist=[],
            agent_socket_operational=True,
            connections=[],
        ),
        fail_state,
    )
    assert isinstance(result, Result)
    assert result.state == fail_state
    assert result.summary == "TLS is not activated on monitored host (see details)"


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_no_controller(fail_state: State) -> None:
    assert not [*_check_transport(False, None, fail_state)]


@pytest.mark.parametrize("fail_state", list(State))
def test_check_tranport_via_ssh(fail_state: State) -> None:
    assert [*_check_transport(True, None, fail_state)] == [
        Result(state=State.OK, summary="Transport via SSH")
    ]


def test_check_no_check_yet() -> None:
    """this is the pre 2.2 fromat"""
    assert [
        *_check_cmk_agent_update(
            {},
            {
                "agentupdate": "aghash None last_update None pending_hash None update_url foo last_check None error None"
            },
            None,
        )
    ] == [
        Result(state=State.WARN, summary="No successful connect to server yet"),
        Result(state=State.OK, notice="Update URL: foo"),
    ]


def test_check_no_check_yet_pydantic() -> None:
    assert [
        *_check_cmk_agent_update(
            {},
            None,
            CMKAgentUpdateSection(
                aghash=None,
                last_update=None,
                pending_hash=None,
                update_url="foo",
                last_check=None,
                error=None,
            ),
        )
    ] == [
        Result(state=State.WARN, summary="No successful connect to server yet"),
        Result(state=State.OK, notice="Update URL: foo"),
    ]


@pytest.mark.parametrize(
    "cmk_hostname,agent_updater_hostname,expected_result",
    (
        (
            "some_hostname",
            "some_hostname",
            [Result(state=State.OK, notice="Hostname used by cmk-update-agent: some_hostname")],
        ),
        (
            "some_other_hostname",
            "some_hostname",
            [
                Result(state=State.OK, notice="Hostname used by cmk-update-agent: some_hostname"),
                Result(
                    state=State.CRIT,
                    notice="Hostname defined in Checkmk (some_other_hostname) and cmk-update-agent configuration (some_hostname) do not match",
                ),
            ],
        ),
    ),
)
def test_check_cmk_agent_update(
    cmk_hostname: str,
    agent_updater_hostname: str,
    expected_result: list[Result],
) -> None:
    assert [
        *_check_cmk_agent_update(
            {"host_name": cmk_hostname},
            None,
            CMKAgentUpdateSection(
                aghash=None,
                last_update=None,
                pending_hash=None,
                update_url=None,
                last_check=None,
                error=None,
                host_name=agent_updater_hostname,
            ),
        )
    ] == [Result(state=State.WARN, summary="No successful connect to server yet"), *expected_result]


@pytest.mark.parametrize(
    "trusted_certs,results",
    (
        (None, []),  # no cert details, pre 2.2 updater
        ({}, [Result(state=State.OK, notice="Agent updater has no trusted agent signature keys")]),
        (
            {
                0: {"corrupt": True},
            },
            [
                Result(state=State.OK, notice="Agent signature key #0 is corrupt"),
                Result(state=State.OK, notice="Agent updater has no trusted agent signature keys"),
            ],
        ),
        (
            {
                0: {
                    "corrupt": False,
                    "not_after": "20430525111300Z",
                    "signature_algorithm": "sha1WithRSAEncryption",
                    "common_name": "foo",
                },
            },
            [
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #0 ('foo') will expire: 42 years 9 days",  # timespan apparently does not care for leap years
                ),
                Result(
                    state=State.OK,
                    notice="Time until all agent signature keys are expired: 42 years 9 days",
                ),
            ],
        ),
        (
            {
                0: {"corrupt": True},
                1: {
                    "corrupt": False,
                    "not_after": "20430525111300Z",
                    "signature_algorithm": "sha1WithRSAEncryption",
                    "common_name": "foo",
                },
            },
            [
                Result(state=State.OK, notice="Agent signature key #0 is corrupt"),
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #1 ('foo') will expire: 42 years 9 days",
                ),
                Result(
                    state=State.OK,
                    notice="Time until all agent signature keys are expired: 42 years 9 days",
                ),
            ],
        ),
        (
            {
                0: {
                    "corrupt": False,
                    "not_after": "20430525111300Z",
                    "signature_algorithm": "sha1WithRSAEncryption",
                    "common_name": "foo",
                },
                1: {
                    "corrupt": False,
                    "not_after": "20000525111300Z",
                    "signature_algorithm": "sha1WithRSAEncryption",
                    "common_name": "bar",
                },
                2: {
                    "corrupt": False,
                    "not_after": "20010601111300Z",
                    "signature_algorithm": "sha1WithRSAEncryption",
                    "common_name": "foobar",
                },
            },
            [
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #0 ('foo') will expire: 42 years 9 days",
                ),
                Result(
                    state=State.OK,
                    notice="Agent signature key #1 ('bar') is expired",
                ),
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #2 ('foobar') will expire: 6 days 21 hours",
                ),
                Result(
                    state=State.OK,
                    notice="Time until all agent signature keys are expired: 42 years 9 days",
                ),
            ],
        ),
        (
            {
                0: {
                    "corrupt": True,
                    "not_after": None,
                    "signature_algorithm": None,
                    "common_name": None,
                },
                1: {
                    "corrupt": False,
                    "not_after": "2023-12-20T09:22:17+00:00",
                    "signature_algorithm": "sha512",
                    "common_name": "signed",
                },
                2: {
                    "corrupt": False,
                    "not_after": "2023-12-20T09:28:55+00:00",
                    "signature_algorithm": "sha1",
                    "common_name": "Lorem ipsum",
                },
            },
            [
                Result(state=State.OK, notice="Agent signature key #0 is corrupt"),
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #1 ('signed') will expire: 22 years 213 days",
                ),
                Result(
                    state=State.OK,
                    notice="Time until agent signature key #2 ('Lorem ipsum') will expire: 22 years 213 days",
                ),
                Result(
                    state=State.OK,
                    notice="Time until all agent signature keys are expired: 22 years 213 days",
                ),
            ],
        ),
    ),
)
def test_certificate_results(
    trusted_certs: dict[int, dict[str, bool | str]] | None, results: Iterable[CheckResult]
) -> None:
    # no cert details
    section = _parse_cmk_update_agent_status(
        [
            [
                json.dumps(
                    {
                        "aghash": None,
                        "last_update": None,
                        "pending_hash": None,
                        "update_url": "foo",
                        "last_check": 990789180,  # Fri 2001-05-25 11:13:00 GMT+0000
                        "trusted_certs": trusted_certs,
                        "error": None,
                    }
                )
            ]
        ]
    )

    with time_machine.travel(datetime(2001, 5, 25, 13, 13, 13, tzinfo=ZoneInfo("UTC"))):
        assert [*_check_cmk_agent_update({}, None, section)] == [
            Result(state=State.OK, notice="Time since last update check: 2 hours 0 minutes"),
            Result(state=State.OK, notice="Last update check: 2001-05-25 11:13:00"),
            Result(state=State.OK, notice="Update URL: foo"),
            *results,
        ]


@pytest.mark.parametrize("duplicate", [False, True])
def test_check_warn_upon_old_update_check(duplicate: bool) -> None:
    with time_machine.travel(datetime.fromtimestamp(1645800081.5039608, tz=ZoneInfo("UTC"))):
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
                            "error 503 Server Error: Service Unavailable\nSomething for second line",
                        )
                    )
                },
                None,
            )
        )

    assert actual == [
        Result(
            state=State.WARN,
            summary="Update error: 503 Server Error: Service Unavailable",
            details="503 Server Error: Service Unavailable\nSomething for second line",
        ),
        Result(
            state=State.WARN,
            summary="Time since last update check: 9 days 6 hours (warn/crit at 2 days 0 hours/never)",
        ),
        Result(state=State.OK, notice="Last update check: 2022-02-16 08:28:01"),
        Result(state=State.OK, summary="Last update: 2022-02-16 08:29:41"),
        Result(state=State.OK, notice="Update URL: https://server/site/check_mk"),
        Result(state=State.OK, notice="Agent configuration: 38bf6e44175732bc"),
        Result(state=State.OK, notice="Pending installation: 1234abcd5678efgh"),
    ]


def test_get_error_result() -> None:
    assert list(
        _get_error_result(
            "agent updates are disabled for host name my-host because it is on the exclusion list",
            {"error_deployment_disabled_for_hostname": 0},
        )
    ) == [
        Result(
            state=State.OK,
            summary="agent updates are disabled for host name my-host because it is on the exclusion list",
        ),
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
                    Plugin(
                        name="plugin3",
                        version="unversioned",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
                local_checks=[],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plug-ins: 3",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 0",
                ),
            ],
            id="agent plug-ins only",
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
                    Plugin(
                        name="check3.py",
                        version="unversioned",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plug-ins: 0",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 3",
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
                    Plugin(
                        name="custom_plugin4",
                        version="unversioned",
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
                    Plugin(
                        name="check4.py",
                        version="unversioned",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plug-ins: 4",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 4",
                ),
                Result(
                    state=State.OK,
                    notice="Agent plug-in 'plugin1': 2.1.0i1",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plug-in 'plugin2': 2.0.0p20 (warn/crit below 2.0.0p21/2.0.0p15)",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="Agent plug-in 'custom_plugin3': unable to parse version '??'",
                ),
                Result(
                    state=State.OK,
                    notice="Agent plug-in 'custom_plugin4': no version specified",
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
                Result(
                    state=State.OK,
                    notice="Local check 'check4.py': no version specified",
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
                    Plugin(
                        name="custom_plugin4",
                        version="unversioned",
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
                    Plugin(
                        name="check4.py",
                        version="unversioned",
                        version_int=None,
                        cache_interval=None,
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    summary="Agent plug-ins: 4",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 4",
                ),
                Result(
                    state=State.OK,
                    notice="Agent plug-in 'plugin1': 2.1.0i1",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plug-in 'plugin2': 2.0.0p20 (warn/crit below 2.0.0p21/2.0.0p15)",
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
                    state=State.OK,
                    notice="Local check 'check4.py': no version specified",
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
                    summary="Agent plug-ins: 3",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 3",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plug-in plugin1: found 2 times",
                    details="Consult the HW/SW Inventory for a complete list of files",
                ),
                Result(
                    state=State.WARN,
                    summary="Local check check2.py: found 2 times",
                    details="Consult the HW/SW Inventory for a complete list of files",
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
                    summary="Agent plug-ins: 4",
                ),
                Result(
                    state=State.OK,
                    summary="Local checks: 4",
                ),
                Result(
                    state=State.WARN,
                    summary="Agent plug-in plugin1: found 2 times",
                    details="Consult the HW/SW Inventory for a complete list of files",
                ),
                Result(
                    state=State.WARN,
                    summary="Local check check1.sh: found 2 times",
                    details="Consult the HW/SW Inventory for a complete list of files",
                ),
            ],
            id="duplicate files with excludes",
        ),
    ],
)
def test_check_plugins(
    params: Mapping[str, Any],
    section_plugins: PluginSection | None,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_checkmk_agent(
                params,
                None,
                section_plugins,
                None,
                None,
                None,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    [
        "controller_section",
        "expected_result",
    ],
    [
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[],
            ),
            [],
            id="No data about the certificate available.",
        ),
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id="localhost/heute",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime(2028, 1, 24, 15, 20, 54, tzinfo=UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    notice="Time until controller certificate for `localhost/heute`, issued by `Site 'heute' local CA`, expires: 5 years 0 days",
                )
            ],
            id="Certificate valid for more than 30 days -> Result is OK.",
        ),
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id="localhost/heute",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime(2023, 2, 14, 15, 20, 54, tzinfo=UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                ],
            ),
            [
                Result(
                    state=State.WARN,
                    summary="Time until controller certificate for `localhost/heute`, issued by `Site 'heute' local CA`, expires: 20 days 22 hours (warn/crit below 30 days 0 hours/15 days 0 hours)",
                )
            ],
            id="Certificate valid for less than 30 days -> Result is WARN.",
        ),
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id="localhost/heute",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime(2023, 2, 1, 15, 20, 54, tzinfo=UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                ],
            ),
            [
                Result(
                    state=State.CRIT,
                    summary="Time until controller certificate for `localhost/heute`, issued by `Site 'heute' local CA`, expires: 7 days 22 hours (warn/crit below 30 days 0 hours/15 days 0 hours)",
                )
            ],
            id="Certificate valid for less than 15 days -> Result is CRIT.",
        ),
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id=None,
                        coordinates="localhost:8000/heute",
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime(3021, 5, 27, 15, 20, 40, tzinfo=UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    notice="Time until controller certificate for `localhost/heute`, issued by `Site 'heute' local CA`, expires: 998 years 364 days",
                )
            ],
            id="Legacy (2.1) case",
        ),
        pytest.param(
            ControllerSection(
                allow_legacy_pull=False,
                agent_socket_operational=True,
                ip_allowlist=[],
                connections=[
                    Connection(
                        site_id=None,
                        coordinates=None,
                        local=LocalConnectionStatus(
                            cert_info=CertInfoController(
                                to=datetime(2028, 1, 24, 15, 20, 54, tzinfo=UTC),
                                issuer="Site 'heute' local CA",
                            )
                        ),
                    ),
                ],
            ),
            [
                Result(
                    state=State.OK,
                    notice="Time until controller certificate issued by `Site 'heute' local CA` (imported connection) expires: 5 years 0 days",
                )
            ],
            id="Imported connection",
        ),
    ],
)
def test_certificate_validity(
    controller_section: ControllerSection,
    expected_result: CheckResult,
) -> None:
    with time_machine.travel(datetime.fromtimestamp(1674578645.3644419, tz=ZoneInfo("UTC"))):
        assert (
            list(check_checkmk_agent({}, None, None, controller_section, None, None))
            == expected_result
        )


@pytest.mark.parametrize(
    [
        "section_cached_plugins",
        "expected_result",
    ],
    [
        pytest.param(
            CachedPluginsSection(
                timeout=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.PLUGIN,
                        plugin_name="some_plugin",
                        timeout=123,
                        pid=4711,
                    ),
                ],
                killfailed=None,
            ),
            [
                Result(
                    state=State.WARN,
                    summary="Timed out plugin(s): some_plugin",
                    details="Cached plugins(s) that reached timeout: some_plugin (Agent plug-in, Timeout: 123s, PID: 4711) - "
                    "Corresponding output is outdated and/or dropped.",
                ),
            ],
            id="timeout_agent_plugin",
        ),
        pytest.param(
            CachedPluginsSection(
                timeout=None,
                killfailed=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.LOCAL,
                        plugin_name="my_local_check",
                        timeout=7200,
                        pid=1234,
                    ),
                ],
            ),
            [
                Result(
                    state=State.WARN,
                    summary="Termination failed: my_local_check",
                    details="Cached plugins(s) that failed to be terminated after timeout: "
                    "my_local_check (Local check, Timeout: 7200s, PID: 1234) - Dysfunctional until successful termination.",
                ),
            ],
            id="killfailed_local_check",
        ),
        pytest.param(
            CachedPluginsSection(
                timeout=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.PLUGIN,
                        plugin_name="some_plugin",
                        timeout=7200,
                        pid=1234,
                    ),
                    CachedPlugin(
                        plugin_type=None,
                        plugin_name="other_process",
                        timeout=7200,
                        pid=1234,
                    ),
                ],
                killfailed=[
                    CachedPlugin(
                        plugin_type=CachedPluginType.LOCAL,
                        plugin_name="my_local_check",
                        timeout=7200,
                        pid=1234,
                    ),
                    CachedPlugin(
                        plugin_type=CachedPluginType.ORACLE,
                        plugin_name="destroy_db",
                        timeout=123,
                        pid=4711,
                    ),
                ],
            ),
            [
                Result(
                    state=State.WARN,
                    summary="Timed out plugin(s): some_plugin, other_process",
                    details="Cached plugins(s) that reached timeout: some_plugin (Agent plug-in, Timeout: 7200s, PID: 1234), "
                    "other_process (Timeout: 7200s, PID: 1234) - Corresponding output is outdated and/or dropped.",
                ),
                Result(
                    state=State.WARN,
                    summary="Termination failed: my_local_check, destroy_db",
                    details="Cached plugins(s) that failed to be terminated after timeout: "
                    "my_local_check (Local check, Timeout: 7200s, PID: 1234), destroy_db (mk_oracle plug-in, Timeout: 123s, PID: 4711) - "
                    "Dysfunctional until successful termination.",
                ),
            ],
            id="timeout_and_killfailed",
        ),
    ],
)
def test_cached_plugins(
    section_cached_plugins: CachedPluginsSection | None,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_checkmk_agent(
                {},
                None,
                None,
                None,
                None,
                section_cached_plugins,
            )
        )
        == expected_result
    )


def test_expand_curly_address_notation() -> None:
    assert expand_curly_address_notation("1.2.{3,4,5}.6") == ["1.2.3.6", "1.2.4.6", "1.2.5.6"]
    assert expand_curly_address_notation(["0.0.0.0", "1.1.1.1/32"]) == ["0.0.0.0", "1.1.1.1/32"]
    assert expand_curly_address_notation("0.0.0.0 1.1.1.1/32") == ["0.0.0.0", "1.1.1.1/32"]
