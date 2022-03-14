#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

import cmk.base.plugins.agent_based.docker_container_status as docker
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResults, Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
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


@pytest.mark.parametrize(
    "string_table, parse_type",
    [
        (STRING_TABLE_WITH_VERSION, dict),
    ],
)
def test_parse_docker_container_status(string_table, parse_type):
    actual_parsed = docker.parse_docker_container_status(string_table)
    assert actual_parsed == PARSED
    assert isinstance(actual_parsed, parse_type)


@pytest.mark.parametrize(
    "string_table, exception_type",
    [
        (STRING_TABLE_WITHOUT_VERSION, AgentOutputMalformatted),
    ],
)
def test_parse_docker_container_status_legacy_raises(string_table, exception_type):
    with pytest.raises(exception_type):
        docker.parse_docker_container_status(string_table)


def _test_discovery(discovery_function, section, expected_discovery):
    for status in ["running", "exited"]:
        assert list(discovery_function({**section, "Status": status})) == expected_discovery


def test_discovery_docker_container_status():
    _test_discovery(
        docker.discover_docker_container_status,
        PARSED,
        [Service(item=None, parameters={}, labels=[])],
    )


def test_check_docker_container_status():
    expected_results = [Result(state=state.OK, summary="Container running")]
    assert list(docker.check_docker_container_status(PARSED)) == expected_results


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


@pytest.mark.parametrize(
    "params, expected_results",
    [
        (
            {},
            [
                Result(state=state.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(state=state.OK, summary="Uptime: 1 hour 1 minute"),
                Metric("uptime", 3713.0),
            ],
        ),
        (
            {"min": (1000, 2000)},
            [
                Result(state=state.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(state=state.OK, summary="Uptime: 1 hour 1 minute"),
                Metric("uptime", 3713.0),
            ],
        ),
        (
            {"max": (1000, 2000)},
            [
                Result(state=state.OK, summary="Up since Jun 05 2019 08:58:07"),
                Result(
                    state=state.CRIT,
                    summary="Uptime: 1 hour 1 minute (warn/crit at 16 minutes 40 seconds/33 minutes 20 seconds)",
                ),
                Metric("uptime", 3713.0, levels=(1000.0, 2000.0)),
            ],
        ),
    ],
)
def test_check_docker_container_status_uptime(params, expected_results):
    with on_time(*NOW_SIMULATED):
        yielded_results = list(docker.check_docker_container_status_uptime(params, PARSED, None))
        assert expected_results == yielded_results


def test_discover_docker_container_status_health():
    _test_discovery(
        docker.discover_docker_container_status_health,
        PARSED,
        [Service()],
    )


@pytest.mark.parametrize(
    "section, expected",
    [
        (
            PARSED,
            [
                Result(
                    state=state.CRIT,
                    summary="Health status: Unhealthy",
                ),
                Result(
                    state=state.OK,
                    summary="Last health report: mysqld is alive",
                ),
                Result(state=state.CRIT, summary="Failing streak: 0"),
                Result(
                    state=state.OK,
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
                Result(state=state.OK, summary="Health status: Healthy"),
                Result(state=state.WARN, summary="Last health report: no output"),
                Result(
                    state=state.OK,
                    summary="Health test: CMD-SHELL",
                    details="Health test: CMD-SHELL #!/bin/bash\n\nexit $(my_healthcheck)\n",
                ),
            ],
        ),
    ],
)
def test_check_docker_container_status_health(section, expected):
    yielded_results = list(docker.check_docker_container_status_health(section))
    assert yielded_results == expected
