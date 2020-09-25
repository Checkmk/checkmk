#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import on_time  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    State as state,
    Result,
    IgnoreResults,
    Metric,
)
import cmk.base.plugins.agent_based.docker_container_status as docker
from cmk.base.plugins.agent_based.utils.legacy_docker import DeprecatedDict
NOW_SIMULATED = 1559728800, "UTC"
STRING_TABLE_WITH_VERSION = [
    [
        '@docker_version_info',
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.39"}'
    ],
    [
        '{"Status": "running", "Healthcheck": {"Test": ["CMD-SHELL", "/healthcheck.sh"]}, "Pid": 0, "OOMKilled": false, "Dead": false, "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"}, "Paused": false, "Running": false, "FinishedAt": "2019-06-05T13:52:46.75115293Z", "Health": {"Status": "unhealthy", "Log": [{"Start": "2019-06-05T15:50:23.329542773+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:23.703382311+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:50:53.724749309+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:54.082847699+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:24.10105535+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:24.479921663+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:54.531087549+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:54.891176872+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:52:24.911587947+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:52:25.256847222+02:00", "ExitCode": 0}], "FailingStreak": 0}, "Restarting": false, "Error": "", "StartedAt": "2019-06-05T08:58:06.893459004Z", "ExitCode": 0}'
    ]
]

STRING_TABLE_WITHOUT_VERSION = STRING_TABLE_WITH_VERSION[1:]

PARSED = {
    'Dead': False,
    'Error': '',
    'ExitCode': 0,
    'FinishedAt': '2019-06-05T13:52:46.75115293Z',
    'Health': {
        'FailingStreak': 0,
        'Log': [{
            'End': '2019-06-05T15:50:23.703382311+02:00',
            'ExitCode': 0,
            'Output': 'mysqld is alive\n',
            'Start': '2019-06-05T15:50:23.329542773+02:00'
        }, {
            'End': '2019-06-05T15:50:54.082847699+02:00',
            'ExitCode': 0,
            'Output': 'mysqld is alive\n',
            'Start': '2019-06-05T15:50:53.724749309+02:00'
        }, {
            'End': '2019-06-05T15:51:24.479921663+02:00',
            'ExitCode': 0,
            'Output': 'mysqld is alive\n',
            'Start': '2019-06-05T15:51:24.10105535+02:00'
        }, {
            'End': '2019-06-05T15:51:54.891176872+02:00',
            'ExitCode': 0,
            'Output': 'mysqld is alive\n',
            'Start': '2019-06-05T15:51:54.531087549+02:00'
        }, {
            'End': '2019-06-05T15:52:25.256847222+02:00',
            'ExitCode': 0,
            'Output': 'mysqld is alive\n',
            'Start': '2019-06-05T15:52:24.911587947+02:00'
        }],
        'Status': 'unhealthy'
    },
    'Healthcheck': {
        'Test': ['CMD-SHELL', '/healthcheck.sh']
    },
    'OOMKilled': False,
    'Paused': False,
    'Pid': 0,
    'RestartPolicy': {
        'MaximumRetryCount': 0,
        'Name': 'no'
    },
    'Restarting': False,
    'Running': False,
    'StartedAt': '2019-06-05T08:58:06.893459004Z',
    'Status': 'running',
}
PARSED_NOT_RUNNING = {"Status": "stopped"}


@pytest.mark.parametrize("string_table, parse_type", [
    (STRING_TABLE_WITH_VERSION, dict),
    (STRING_TABLE_WITHOUT_VERSION, DeprecatedDict),
])
def test_parse_docker_container_status(string_table, parse_type):
    actual_parsed = docker.parse_docker_container_status(string_table)
    assert actual_parsed == PARSED
    assert isinstance(actual_parsed, parse_type)


def test_discovery_docker_container_status():
    expected_discovery = [
        Service(item=None, parameters={}, labels=[]),
    ]

    assert list(docker.discover_docker_container_status(PARSED)) == expected_discovery


def test_check_docker_container_status():
    expected_results = [
        Result(state=state.OK, summary='Container running', details='Container running')
    ]
    assert list(docker.check_docker_container_status(PARSED)) == expected_results


@pytest.mark.parametrize("section_uptime, expected_services", [
    (
        {
            "an uptime section": 123456789
        },
        [],
    ),
    (
        {},
        [
            Service(item=None, parameters={}, labels=[]),
        ],
    ),
])
def test_discovery_docker_container_status_uptime(section_uptime, expected_services):
    assert list(docker.discover_docker_container_status_uptime(PARSED,
                                                               section_uptime)) == expected_services


@pytest.mark.parametrize("params, expected_results", [
    ({}, [
        Result(state=state.OK,
               summary='Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute',
               details='Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute'),
        Metric('uptime', 3713.0, levels=(None, None), boundaries=(None, None)),
    ]),
    ({
        "min": (1000, 2000)
    }, [
        Result(state=state.OK,
               summary='Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute',
               details='Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute'),
        Metric('uptime', 3713.0, levels=(None, None), boundaries=(None, None)),
    ]),
    ({
        "max": (1000, 2000)
    }, [
        Result(
            state=state.CRIT,
            summary=
            'Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute (warn/crit at 16 minutes 40 seconds/33 minutes 20 seconds)',
            details=
            'Up since Jun 05 2019 08:58:07, Uptime:: 1 hour 1 minute (warn/crit at 16 minutes 40 seconds/33 minutes 20 seconds)'
        ),
        Metric('uptime', 3713.0, levels=(1000.0, 2000.0), boundaries=(None, None)),
    ]),
])
def test_check_docker_container_status_uptime(params, expected_results):
    with on_time(*NOW_SIMULATED):
        yielded_results = list(docker.check_docker_container_status_uptime(params, PARSED, {}))
        assert expected_results == yielded_results


def test_discover_docker_container_status_health():

    yielded_services = list(docker.discover_docker_container_status_health(PARSED))
    expected_services = [Service()]
    assert yielded_services == expected_services


@pytest.mark.parametrize("section, expected", [
    (PARSED, [
        Result(state=state.CRIT,
               summary='Health status: Unhealthy',
               details='Health status: Unhealthy'),
        Result(state=state.OK,
               summary='Last health report: mysqld is alive',
               details='Last health report: mysqld is alive'),
        Result(state=state.CRIT, summary='Failing streak: 0', details='Failing streak: 0'),
        Result(state=state.OK,
               summary='Health test: CMD-SHELL /healthcheck.sh',
               details='Health test: CMD-SHELL /healthcheck.sh')
    ]),
    (PARSED_NOT_RUNNING, [
        IgnoreResults("Container is not running"),
    ]),
])
def test_check_docker_container_status_health(section, expected):
    import pprint as pp
    pp.pprint(section)
    yielded_results = list(docker.check_docker_container_status_health(section))
    assert repr(yielded_results) == repr(expected)
