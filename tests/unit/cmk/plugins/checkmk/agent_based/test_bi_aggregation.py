#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.checkmk.agent_based.bi_aggregation import check_bi_aggregation

TEST_INFO = {
    "Host test": {
        "state": 1,
        "output": "",
        "hosts": ["test"],
        "acknowledged": False,
        "in_downtime": False,
        "in_service_period": True,
        "infos": [
            {"error": {"state": 1, "output": "Host test"}},
            [
                [
                    {"error": {"state": 1, "output": "General State"}},
                    [
                        [
                            {"error": {"state": 1, "output": "Check_MK"}},
                            [
                                [
                                    {
                                        "error": {
                                            "state": 1,
                                            "output": "Check_MK Discovery, Services unmonitored: 1 (cpu_loads: 1)(!), Host labels: all up to date",
                                        }
                                    },
                                    [],
                                ]
                            ],
                        ]
                    ],
                ],
                [
                    {},
                    [
                        [
                            {
                                "error": {
                                    "state": 1,
                                    "output": "Aggr Host test, Aggregation state: Warning(!), In downtime: no, Acknowledged: no",
                                }
                            },
                            [],
                        ],
                        [
                            {
                                "error": {
                                    "state": 2,
                                    "output": "OMD test_gestern Notification Spooler, Version: 2.3.0-2024.02.01, Status last updated 42 days 1 hour ago, spooler seems crashed or busy(!!)",
                                }
                            },
                            [],
                        ],
                        [
                            {
                                "error": {
                                    "state": 2,
                                    "output": "OMD stable Notification Spooler, Version: 2.2.0-2024.03.13, Status last updated 22 hours 17 minutes ago, spooler seems crashed or busy(!!)",
                                }
                            },
                            [],
                        ],
                    ],
                ],
            ],
        ],
        "state_computed_by_agent": 1,
    }
}


def test_check_bi_aggregation() -> None:
    assert list(check_bi_aggregation("Host test", TEST_INFO)) == [
        Result(state=State.WARN, summary="Aggregation state: Warning"),
        Result(state=State.OK, summary="In downtime: no"),
        Result(state=State.OK, summary="Acknowledged: no"),
        Result(state=State.OK, notice="Aggregation problems affecting the state:"),
        Result(state=State.WARN, notice="Host test"),
        Result(state=State.WARN, notice="General State", details="+-- General State"),
        Result(state=State.WARN, notice="Check_MK", details="| +-- Check_MK"),
        Result(
            state=State.WARN,
            notice="Check_MK Discovery, Services unmonitored: 1 (cpu_loads: 1)(!), Host labels: all up to date",
            details="| | +-- Check_MK Discovery, Services unmonitored: 1 (cpu_loads: 1)(!), Host labels: all up to date",
        ),
        Result(state=State.OK, notice="Aggregation problems not affecting the state:"),
        Result(
            state=State.WARN,
            notice="Aggr Host test, Aggregation state: Warning(!), In downtime: no, Acknowledged: no",
            details="+-- +-- Aggr Host test, Aggregation state: Warning(!), In downtime: no, Acknowledged: no",
        ),
        Result(
            state=State.CRIT,
            notice="OMD test_gestern Notification Spooler, Version: 2.3.0-2024.02.01, Status last updated 42 days 1 hour ago, spooler seems crashed or busy(!!)",
            details="| +-- OMD test_gestern Notification Spooler, Version: 2.3.0-2024.02.01, Status last updated 42 days 1 hour ago, spooler seems crashed or busy(!!)",
        ),
        Result(
            state=State.CRIT,
            notice="OMD stable Notification Spooler, Version: 2.2.0-2024.03.13, Status last updated 22 hours 17 minutes ago, spooler seems crashed or busy(!!)",
            details="| +-- OMD stable Notification Spooler, Version: 2.2.0-2024.03.13, Status last updated 22 hours 17 minutes ago, spooler seems crashed or busy(!!)",
        ),
    ]
