#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.windows.agent_based.windows_tasks import (
    check_windows_tasks,
    discovery_windows_tasks,
    Params,
    parse_windows_tasks,
)

STRING_TABLE = [
    ["TaskName             ", " Monitoring - Content Replication get failed"],
    ["and outdated items"],
    ["Last Run Time        ", " 7/21/2020 6", "30", "02 AM"],
    ["Next Run Time        ", " 7/22/2020 6", "30", "00 AM"],
    ["Last Result          ", " 0"],
    ["Scheduled Task State ", " Enabled"],
    ["TaskName             ", " Monitoring - Content Replicaton status"],
    ["reporting overall"],
    ["Last Run Time        ", " 7/21/2020 6", "45", "02 AM"],
    ["Next Run Time        ", " 7/22/2020 6", "45", "00 AM"],
    ["Last Result          ", " 0"],
    ["Scheduled Task State ", " Enabled"],
    ["TaskName             ", " Monitoring - Delete old IIS logs"],
    ["Last Run Time        ", " 7/20/2020 10", "00", "01 PM"],
    ["Next Run Time        ", " 7/21/2020 10", "00", "00 PM"],
    ["Last Result          ", " 0"],
    ["Scheduled Task State ", " Enabled"],
    ["TaskName             ", " jherbel-task"],
    ["Last Run Time        ", " 10/26/2020 4", "23", "10 AM"],
    ["Next Run Time        ", " N/A"],
    ["Last Result          ", " 0"],
    ["Scheduled Task State ", " Disabled"],
    ["TaskName             ", " task-unknown-exit-code"],
    ["Last Run Time        ", " 10/26/2020 4", "23", "10 AM"],
    ["Next Run Time        ", " N/A"],
    ["Last Result          ", " -2147024630"],
    ["Scheduled Task State ", " Enabled"],
]

SECTION = {
    "Monitoring - Content Replication get failed and outdated items": {
        "Last Run Time": "7/21/2020 6:30:02 AM",
        "Next Run Time": "7/22/2020 6:30:00 AM",
        "Last Result": "0",
        "Scheduled Task State": "Enabled",
    },
    "Monitoring - Content Replicaton status reporting overall": {
        "Last Run Time": "7/21/2020 6:45:02 AM",
        "Next Run Time": "7/22/2020 6:45:00 AM",
        "Last Result": "0",
        "Scheduled Task State": "Enabled",
    },
    "Monitoring - Delete old IIS logs": {
        "Last Run Time": "7/20/2020 10:00:01 PM",
        "Next Run Time": "7/21/2020 10:00:00 PM",
        "Last Result": "0",
        "Scheduled Task State": "Enabled",
    },
    "jherbel-task": {
        "Last Run Time": "10/26/2020 4:23:10 AM",
        "Next Run Time": "N/A",
        "Last Result": "0",
        "Scheduled Task State": "Disabled",
    },
    "task-unknown-exit-code": {
        "Last Run Time": "10/26/2020 4:23:10 AM",
        "Next Run Time": "N/A",
        "Last Result": "-2147024630",
        "Scheduled Task State": "Enabled",
    },
}


def test_parse() -> None:
    section = parse_windows_tasks(STRING_TABLE)
    assert section == SECTION


def test_discovery() -> None:
    services = list(discovery_windows_tasks({}, SECTION))
    assert services == [
        Service(item="Monitoring - Content Replication get failed and outdated items"),
        Service(item="Monitoring - Content Replicaton status reporting overall"),
        Service(item="Monitoring - Delete old IIS logs"),
        Service(item="task-unknown-exit-code"),
    ]


def test_discovery_rule() -> None:
    section = {
        "task": {
            "Last Run Time": "10/26/2020 4:23:10 AM",
            "Next Run Time": "N/A",
            "Last Result": "-2147024630",
            "Scheduled Task State": "Disabled",
        }
    }
    services = list(discovery_windows_tasks({}, section))
    assert not services
    services = list(discovery_windows_tasks({"discover_disabled": True}, section))
    assert services == [Service(item="task")]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "Monitoring - Content Replication get failed and outdated items",
            {},
            [
                Result(state=State.OK, summary="The task exited successfully (0x00000000)"),
                Result(
                    state=State.OK,
                    summary="Last run time: 7/21/2020 6:30:02 AM, Next run time: 7/22/2020 6:30:00 AM",
                ),
            ],
        ),
        pytest.param(
            "Monitoring - Content Replicaton status reporting overall",
            {},
            [
                Result(
                    state=State.OK,
                    summary="The task exited successfully (0x00000000)",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 7/21/2020 6:45:02 AM, Next run time: 7/22/2020 6:45:00 AM",
                ),
            ],
        ),
        pytest.param(
            "Monitoring - Delete old IIS logs",
            {},
            [
                Result(
                    state=State.OK,
                    summary="The task exited successfully (0x00000000)",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM",
                ),
            ],
        ),
        pytest.param(
            "Monitoring - Delete old IIS logs",
            {
                "exit_code_to_state": [
                    {
                        "exit_code": "0x00000000",
                        "monitoring_state": 1,
                    }
                ]
            },
            [
                Result(
                    state=State.WARN,
                    summary="The task exited successfully (0x00000000)",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM",
                ),
            ],
        ),
        pytest.param(
            "Monitoring - Delete old IIS logs",
            {
                "exit_code_to_state": [
                    {
                        "exit_code": "0x00000000",
                        "monitoring_state": 1,
                        "info_text": "Something else",
                    }
                ]
            },
            [
                Result(
                    state=State.WARN,
                    summary="Something else (0x00000000)",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM",
                ),
            ],
        ),
        pytest.param(
            "jherbel-task",
            {},
            [
                Result(
                    state=State.OK,
                    summary="The task exited successfully (0x00000000)",
                ),
                Result(
                    state=State.WARN,
                    summary="Task not enabled",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A",
                ),
            ],
        ),
        pytest.param(
            "jherbel-task",
            {"state_not_enabled": 3},
            [
                Result(
                    state=State.OK,
                    summary="The task exited successfully (0x00000000)",
                ),
                Result(
                    state=State.UNKNOWN,
                    summary="Task not enabled",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A",
                ),
            ],
        ),
        pytest.param(
            "task-unknown-exit-code",
            {},
            [
                Result(
                    state=State.CRIT,
                    summary="Got exit code 0x8007010a",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A",
                ),
            ],
        ),
        pytest.param(
            "task-unknown-exit-code",
            {
                "exit_code_to_state": [
                    {
                        "exit_code": "0x8007010a",
                        "monitoring_state": 0,
                    }
                ]
            },
            [
                Result(
                    state=State.OK,
                    summary="Got exit code 0x8007010a",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A",
                ),
            ],
        ),
        pytest.param(
            "task-unknown-exit-code",
            {
                "exit_code_to_state": [
                    {
                        "exit_code": "0x8007010a",
                        "monitoring_state": 0,
                        "info_text": "Give me your boots and your motorcycle!",
                    }
                ]
            },
            [
                Result(
                    state=State.OK,
                    summary="Give me your boots and your motorcycle! (0x8007010a)",
                ),
                Result(
                    state=State.OK,
                    summary="Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A",
                ),
            ],
        ),
    ],
)
def test_check(item: str, params: Params, expected_result: list[Result]) -> None:
    result = list(check_windows_tasks(item, params, SECTION))
    assert result == expected_result
