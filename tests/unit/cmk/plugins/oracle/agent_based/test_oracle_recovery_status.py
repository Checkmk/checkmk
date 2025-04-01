#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.oracle.agent_based.oracle_recovery_status import (
    check_oracle_recovery_status,
    parse_oracle_recovery_status,
)


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "Error Message:          MyDatabase",
            [
                [
                    "Error Message:          MyDatabase",
                    "FAILURE",
                    "ERROR: ORA-123456: Some kind of error occurred",
                ]
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Error Message:          MyDatabase, FAILURE, ERROR: ORA-123456: Some kind of error occurred",
                )
            ],
        )
    ],
)
def test_check_oracle_recovery_status(
    item: str, info: list[list[str]], expected_result: CheckResult
) -> None:
    assert (
        list(check_oracle_recovery_status(item, {}, parse_oracle_recovery_status(info)))
        == expected_result
    )


def test_check_oracle_recovery_status_good() -> None:
    section = parse_oracle_recovery_status(
        [
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "1",
                "1722989170",
                "717",
                "ONLINE",
                "NO",
                "YES",
                "1966755",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "3",
                "1722989170",
                "717",
                "ONLINE",
                "NO",
                "YES",
                "1966755",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "4",
                "1722989170",
                "717",
                "ONLINE",
                "NO",
                "YES",
                "1966755",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "5",
                "1722988478",
                "1409",
                "ONLINE",
                "",
                "NO",
                "1959981",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "6",
                "1722988478",
                "1409",
                "ONLINE",
                "",
                "NO",
                "1959981",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "7",
                "1722989170",
                "717",
                "ONLINE",
                "NO",
                "YES",
                "1966755",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "8",
                "1722988478",
                "1409",
                "ONLINE",
                "",
                "NO",
                "1959981",
                "NOT ACTIVE",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "9",
                "1722989067",
                "820",
                "ONLINE",
                "",
                "NO",
                "1966021",
                "NOT VERIFIED",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "10",
                "1722989067",
                "820",
                "ONLINE",
                "",
                "NO",
                "1966021",
                "NOT VERIFIED",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "11",
                "1722989067",
                "820",
                "ONLINE",
                "",
                "NO",
                "1966021",
                "NOT VERIFIED",
                "0",
            ],
            [
                "ORCL",
                "orcl",
                "PRIMARY",
                "READ WRITE",
                "12",
                "1722989067",
                "820",
                "ONLINE",
                "",
                "NO",
                "1966021",
                "NOT VERIFIED",
                "0",
            ],
        ]
    )
    assert list(check_oracle_recovery_status("ORCL", {}, section)) == [
        Result(
            state=State.OK, summary="primary database, oldest Checkpoint 23 minutes 29 seconds ago"
        ),
        Metric(
            "checkpoint_age",
            1409,
        ),
        Metric("backup_age", 0.0),
    ]
