#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

import cmk.base.plugins.agent_based.docker_container_status as docker
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils import uptime
from cmk.base.plugins.agent_based.utils.docker import AgentOutputMalformatted

NOW_SIMULATED = 1559728800, "UTC"
STRING_TABLE_WITH_VERSION = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.39"}',
    ],
    [
        '{"Status": "running", "Healthcheck": {"Test": ["CMD-SHELL", "/healthcheck.sh"]}, "Pid": 0, "OOMKilled": false, "Dead": false, "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"}, "Paused": false, "Running": false, "FinishedAt": "2019-06-05T13:52:46.75115293Z", "Health": {"Status": "unhealthy", "Log": [{"Start": "2019-06-05T15:50:23.329542773+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:23.703382311+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:50:53.724749309+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:54.082847699+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:24.10105535+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:24.479921663+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:54.531087549+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:54.891176872+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:52:24.911587947+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:52:25.256847222+02:00", "ExitCode": 0}], "FailingStreak": 0}, "Restarting": false, "Error": "", "StartedAt": "2019-06-05T08:58:06.893459004Z", "ExitCode": 0}'
    ],
]

STRING_TABLE_WITHOUT_VERSION = STRING_TABLE_WITH_VERSION[1:]

PARSED = {
    "Dead": False,
    "Error": "",
    "ExitCode": 0,
    "FinishedAt": "2019-06-05T13:52:46.75115293Z",
    "Health": {
        "FailingStreak": 0,
        "Log": [
            {
                "End": "2019-06-05T15:50:23.703382311+02:00",
                "ExitCode": 0,
                "Output": "mysqld is alive\n",
                "Start": "2019-06-05T15:50:23.329542773+02:00",
            },
            {
                "End": "2019-06-05T15:50:54.082847699+02:00",
                "ExitCode": 0,
                "Output": "mysqld is alive\n",
                "Start": "2019-06-05T15:50:53.724749309+02:00",
            },
            {
                "End": "2019-06-05T15:51:24.479921663+02:00",
                "ExitCode": 0,
                "Output": "mysqld is alive\n",
                "Start": "2019-06-05T15:51:24.10105535+02:00",
            },
            {
                "End": "2019-06-05T15:51:54.891176872+02:00",
                "ExitCode": 0,
                "Output": "mysqld is alive\n",
                "Start": "2019-06-05T15:51:54.531087549+02:00",
            },
            {
                "End": "2019-06-05T15:52:25.256847222+02:00",
                "ExitCode": 0,
                "Output": "mysqld is alive\n",
                "Start": "2019-06-05T15:52:24.911587947+02:00",
            },
        ],
        "Status": "unhealthy",
    },
    "Healthcheck": {"Test": ["CMD-SHELL", "/healthcheck.sh"]},
    "OOMKilled": False,
    "Paused": False,
    "Pid": 0,
    "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"},
    "Restarting": False,
    "Running": False,
    "StartedAt": "2019-06-05T08:58:06.893459004Z",
    "Status": "running",
}
PARSED_NOT_RUNNING = {"Status": "stopped"}
SECTION_MULTIPLE_NODES = docker._MultipleNodesMarker()


def test_parse_docker_container_status() -> None:
    assert docker.parse_docker_container_status(STRING_TABLE_WITH_VERSION) == PARSED


def test_parse_docker_container_status_legacy_raises() -> None:
    with pytest.raises(AgentOutputMalformatted):
        docker.parse_docker_container_status(STRING_TABLE_WITHOUT_VERSION)


def test_parse_docker_container_status_with_oci_error() -> None:
    assert (
        docker.parse_docker_container_status(
            [
                *STRING_TABLE_WITH_VERSION,
                ["OCI runtime exec failed: exec failed:"],
            ]
        )
        == PARSED
    )


def test_parse_docker_container_status_multiple_nodes() -> None:
    assert isinstance(
        docker.parse_docker_container_status(
            [
                *STRING_TABLE_WITH_VERSION,
                *STRING_TABLE_WITH_VERSION,
            ]
        ),
        docker._MultipleNodesMarker,
    )


def _test_discovery(
    discovery_function, section: docker.SectionStandard, expected_discovery
) -> None:
    for status in ["running", "exited"]:
        assert list(discovery_function({**section, "Status": status})) == expected_discovery


def test_discovery_docker_container_status():
    _test_discovery(
        docker.discover_docker_container_status,
        PARSED,
        [Service(item=None, parameters={}, labels=[])],
    )


def test_discover_docker_container_status_multiple_nodes() -> None:
    assert list(docker.discover_docker_container_status(SECTION_MULTIPLE_NODES)) == [
        Service(
            item=None,
            parameters={},
            labels=[],
        )
    ]


def test_check_docker_container_status() -> None:
    expected_results = [Result(state=State.OK, summary="Container running")]
    assert list(docker.check_docker_container_status(PARSED)) == expected_results


def test_check_docker_container_status_multiple_nodes() -> None:
    results = list(docker.check_docker_container_status(SECTION_MULTIPLE_NODES))
    assert len(results) == 1
    assert isinstance((only_res := results[0]), Result)
    assert only_res.state is State.CRIT
    assert (
        only_res.summary
        == "Found data from multiple Docker nodes - see service details for more information"
    )


@pytest.mark.parametrize(
    "section_uptime, expected_services",
    [
        (
            uptime.Section(123456789, None),
            [],
        ),
        (
            {},
            [
                Service(item=None, parameters={}, labels=[]),
            ],
        ),
    ],
)
def test_discovery_docker_container_status_uptime(section_uptime, expected_services):
    _test_discovery(
        lambda parsed: docker.discover_docker_container_status_uptime(parsed, section_uptime),
        PARSED,
        expected_services,
    )


def test_discover_docker_container_status_uptime_multiple_nodes() -> None:
    assert not list(
        docker.discover_docker_container_status_uptime(
            SECTION_MULTIPLE_NODES,
            None,
        ),
    )


@pytest.mark.parametrize(
    ["params", "section", "expected_results"],
    [
        (
            {},
            PARSED,
            [
                Result(state=State.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(state=State.OK, summary="Uptime: 1 hour 1 minute"),
                Metric("uptime", 3713.0),
            ],
        ),
        (
            {"min": (1000, 2000)},
            PARSED,
            [
                Result(state=State.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(state=State.OK, summary="Uptime: 1 hour 1 minute"),
                Metric("uptime", 3713.0),
            ],
        ),
        (
            {"max": (1000, 2000)},
            PARSED,
            [
                Result(state=State.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(
                    state=State.CRIT,
                    summary="Uptime: 1 hour 1 minute (warn/crit at 16 minutes 40 seconds/33 minutes 20 seconds)",
                ),
                Metric("uptime", 3713.0, levels=(1000.0, 2000.0)),
            ],
        ),
        pytest.param(
            {},
            SECTION_MULTIPLE_NODES,
            [],
            id="multiple nodes",
        ),
    ],
)
def test_check_docker_container_status_uptime(
    params,
    section: docker.Section,
    expected_results: CheckResult,
) -> None:
    with on_time(*NOW_SIMULATED):
        yielded_results = list(docker.check_docker_container_status_uptime(params, section, None))
        assert expected_results == yielded_results


def test_discover_docker_container_status_health():
    _test_discovery(
        docker.discover_docker_container_status_health,
        PARSED,
        [Service()],
    )


def test_discover_docker_container_status_health_multiple_nodes() -> None:
    assert not list(
        docker.discover_docker_container_status_health(SECTION_MULTIPLE_NODES),
    )


@pytest.mark.parametrize(
    "section, expected",
    [
        (
            PARSED,
            [
                Result(
                    state=State.CRIT,
                    summary="Health status: Unhealthy",
                ),
                Result(
                    state=State.OK,
                    summary="Last health report: mysqld is alive",
                ),
                Result(state=State.CRIT, summary="Failing streak: 0"),
                Result(
                    state=State.OK,
                    summary="Health test: CMD-SHELL /healthcheck.sh",
                ),
            ],
        ),
        (
            PARSED_NOT_RUNNING,
            [
                IgnoreResults("Container is not running"),
            ],
        ),
        # the health check is a script here:
        (
            {
                "Health": {"Status": "healthy"},
                "Healthcheck": {"Test": ["CMD-SHELL", "#!/bin/bash\n\nexit $(my_healthcheck)\n"]},
                "Status": "running",
            },
            [
                Result(state=State.OK, summary="Health status: Healthy"),
                Result(state=State.WARN, summary="Last health report: no output"),
                Result(
                    state=State.OK,
                    summary="Health test: CMD-SHELL",
                    details="Health test: CMD-SHELL #!/bin/bash\n\nexit $(my_healthcheck)\n",
                ),
            ],
        ),
        pytest.param(
            SECTION_MULTIPLE_NODES,
            [],
            id="multiple nodes",
        ),
    ],
)
def test_check_docker_container_status_health(section, expected):
    yielded_results = list(docker.check_docker_container_status_health(section))
    assert yielded_results == expected
