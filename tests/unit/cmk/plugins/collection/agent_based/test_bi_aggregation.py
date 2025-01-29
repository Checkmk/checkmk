#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.bi_aggregation import check_bi_aggregation

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
    expected_notice = (
        "\n"
        "Aggregation problems affecting the state:\n"
        "(!) Host test\n+-- (!) General State\n"
        "| +-- (!) Check_MK\n"
        "| | +-- (!) Check_MK Discovery, Services unmonitored: 1 (cpu_loads: 1)(!), Host labels: all up to date\n"
        "\n"
        "Aggregation problems not affecting the state:\n"
        "+-- +-- (!) Aggr Host test, Aggregation state: Warning(!), In downtime: no, Acknowledged: no\n"
        "| +-- (!!) OMD test_gestern Notification Spooler, Version: 2.3.0-2024.02.01, Status last updated 42 days 1 hour ago, spooler seems crashed or busy(!!)\n"
        "| +-- (!!) OMD stable Notification Spooler, Version: 2.2.0-2024.03.13, Status last updated 22 hours 17 minutes ago, spooler seems crashed or busy(!!)"
    )
    assert list(check_bi_aggregation("Host test", TEST_INFO)) == [
        Result(state=State.WARN, summary="Aggregation state: Warning"),
        Result(state=State.OK, summary="In downtime: no"),
        Result(state=State.OK, summary="Acknowledged: no"),
        Result(state=State.OK, notice=expected_notice),
    ]
