#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.podman.agent_based.cee.podman_pods import (
    check_podman_pods,
    DEFAULT_PARAMS,
    discover_podman_pods,
    Params,
    parse_podman_pods,
)

_STRING_TABLE = [
    [
        '[{"Cgroup": "machine.slice", "Containers": [{"Id": "728b9e223a9b4da2da1f0827ecf304e7e3dcf75fc164c9565d7007fdf1cb216f", "Names": "eloquent_raman", "Status": "created", "RestartCount": 0}, {"Id": "e4a013abdeb13638d2efe4069a467867ccbeac8d9084b4b382ee9b943fbab15a", "Names": "9de406095406-infra", "Status": "created", "RestartCount": 0}], "Created": "2025-07-20T20:11:03.767207333+02:00", "Id": "9de4060954065ed5080771c9390253d93be4fb13d8b91ed213dd74d75110ac21", "InfraId": "e4a013abdeb13638d2efe4069a467867ccbeac8d9084b4b382ee9b943fbab15a", "Name": "mypod", "Namespace": "", "Networks": ["podman"], "Status": "Created", "Labels": {}}]'
    ],
    [
        '[{"Cgroup": "user.slice", "Containers": [{"Id": "65803698cd3515379fe2a18c8eb9ce12b4be5d637ae0e9110443da3165eecd08", "Names": "4cbae6c3a925-infra", "Status": "created", "RestartCount": 0}], "Created": "2025-07-20T20:05:37.21292926+02:00", "Id": "4cbae6c3a925717948e84b337afd8130432339d604e215fa191e7c6b72ebaf3d", "InfraId": "65803698cd3515379fe2a18c8eb9ce12b4be5d637ae0e9110443da3165eecd08", "Name": "mypod", "Namespace": "", "Networks": [], "Status": "Dead", "Labels": {}}]'
    ],
]


def test_discover_podman_pods():
    assert list(discover_podman_pods(parse_podman_pods(_STRING_TABLE))) == [Service()]


def test_discover_podman_pods_empty_table():
    assert list(discover_podman_pods(parse_podman_pods([[]]))) == [Service()]


@pytest.mark.parametrize(
    "string_table, params, expected_result",
    [
        pytest.param(
            [[]],
            {},
            [Result(state=State.OK, summary="No pods found")],
            id="No pods -> OK",
        ),
        pytest.param(
            _STRING_TABLE,
            {},
            [
                Result(state=State.OK, summary="Total: 2"),
                Metric("podman_pods_total_number", 2.0),
                Result(state=State.OK, summary="Running: 0"),
                Metric("podman_pods_running_number", 0.0),
                Result(state=State.OK, summary="Created: 1"),
                Metric("podman_pods_created_number", 1.0),
                Result(state=State.OK, summary="Stopped: 0"),
                Metric("podman_pods_stopped_number", 0.0),
                Result(state=State.OK, summary="Dead: 1"),
                Metric("podman_pods_dead_number", 1.0),
                Result(state=State.OK, summary="Exited: 0"),
                Metric("podman_pods_exited_number", 0.0),
            ],
            id="No params -> OK",
        ),
        pytest.param(
            _STRING_TABLE,
            DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Total: 2"),
                Metric("podman_pods_total_number", 2.0),
                Result(state=State.OK, summary="Running: 0"),
                Metric("podman_pods_running_number", 0.0),
                Result(state=State.OK, summary="Created: 1"),
                Metric("podman_pods_created_number", 1.0),
                Result(state=State.OK, summary="Stopped: 0"),
                Metric("podman_pods_stopped_number", 0.0),
                Result(state=State.CRIT, summary="Dead: 1 (warn/crit at 1/1)"),
                Metric("podman_pods_dead_number", 1.0, levels=(1.0, 1.0)),
                Result(state=State.OK, summary="Exited: 0"),
                Metric("podman_pods_exited_number", 0.0),
            ],
            id="One dead with params -> CRIT",
        ),
    ],
)
def test_check_podman_pods(
    string_table: StringTable, params: Params, expected_result: CheckResult
) -> None:
    assert list(check_podman_pods(params, parse_podman_pods(string_table))) == expected_result
