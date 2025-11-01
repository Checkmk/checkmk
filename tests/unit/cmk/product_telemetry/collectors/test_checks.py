#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from pytest_mock import MockType

from livestatus import LivestatusResponse

import cmk.product_telemetry.collectors.checks as checks_collector
from cmk.product_telemetry.exceptions import ServicesInfoLengthError
from cmk.product_telemetry.schema import Checks


@pytest.mark.parametrize(
    ("livestatus_response", "expected_data"),
    [
        (
            [
                [0, "test_host_1", "test_command_1"],
                [0, "test_host_1", "test_command_1"],
                [0, "test_host_1", "test_command_2"],
                [0, "test_host_2", "test_command_1"],
            ],
            {
                "test_command_1": {"count": 3, "count_hosts": 2, "count_disabled": 0},
                "test_command_2": {"count": 1, "count_hosts": 1, "count_disabled": 0},
            },
        ),
        (
            [],
            {},
        ),
    ],
)
@pytest.mark.usefixtures("mock_instance_id")
def test_get_services(
    livestatus_response: LivestatusResponse, expected_data: Checks, local_connection: MockType
) -> None:
    local_connection.query.return_value = livestatus_response

    data = checks_collector._get_services(local_connection)

    assert data == expected_data


@pytest.mark.usefixtures("mock_instance_id")
def test_get_services_unexpected_result_or_column(local_connection: MockType) -> None:
    local_connection.query.return_value = [[0]]
    with pytest.raises(ServicesInfoLengthError):
        checks_collector._get_services(local_connection)


@pytest.mark.parametrize(
    ("livestatus_response", "expected_data"),
    [
        (
            [
                [
                    "Service ignored: test_command_1: Test Check Output",
                ],
                [
                    "Service ignored: test_command_1: Test Check Output",
                ],
            ],
            {
                "test_command_1": {"count": 0, "count_hosts": 0, "count_disabled": 2},
            },
        ),
        (
            [["0", "test_host_1", "test_command_1"]],
            {},
        ),
        (
            [
                [
                    "Service ignored: test_command_1: Test Check Output\u000aService ignored: test_command_2: Test Check Output",
                ],
                [
                    "Service ignored: test_command_2: Test Check Output",
                ],
            ],
            {
                "test_command_1": {"count": 0, "count_hosts": 0, "count_disabled": 1},
                "test_command_2": {"count": 0, "count_hosts": 0, "count_disabled": 2},
            },
        ),
    ],
)
def test_get_disabled_services(
    livestatus_response: LivestatusResponse, expected_data: Checks, local_connection: MockType
) -> None:
    local_connection.query.return_value = livestatus_response

    data = checks_collector._get_disabled_services(local_connection)

    assert data == expected_data


def test_merge_check_data() -> None:
    checks1: Checks = {
        "test_command_1": {"count": 1, "count_hosts": 1, "count_disabled": 1},
        "test_command_2": {"count": 10, "count_hosts": 0, "count_disabled": 1},
    }
    checks2: Checks = {
        "test_command_1": {"count": 0, "count_hosts": 0, "count_disabled": 0},
        "test_command_2": {"count": 1, "count_hosts": 10, "count_disabled": 1},
    }
    merged_checks: Checks = {
        "test_command_1": {"count": 1, "count_hosts": 1, "count_disabled": 1},
        "test_command_2": {"count": 11, "count_hosts": 10, "count_disabled": 2},
    }
    assert checks_collector.merge_check_data(checks1, checks2) == merged_checks
