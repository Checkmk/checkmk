#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_recovery_status import (
    check_oracle_recovery_status,
    discover_oracle_recovery_status,
    parse_oracle_recovery_status,
)

_FAILURE = [["ORCL", "FAILURE", "ORA-00942: table or view does not exist"]]


def test_check_surfaces_failure() -> None:
    assert list(
        check_oracle_recovery_status("ORCL", {}, parse_oracle_recovery_status(_FAILURE))
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_failure_row_wins_over_data_row() -> None:
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
        ]
        + _FAILURE
    )
    assert list(check_oracle_recovery_status("ORCL", {}, section)) == [
        Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")
    ]


def test_check_row_of_unknown_length_is_crit_with_the_raw_row() -> None:
    section = parse_oracle_recovery_status(
        [["TUX2", "tux2", "PRIMARY", "MOUNTED", "1", "1405456155", "ONLINE", "", "NO", "2719061"]]
    )
    assert list(check_oracle_recovery_status("TUX2", {}, section)) == [
        Result(
            state=State.CRIT,
            summary="TUX2, tux2, PRIMARY, MOUNTED, 1, 1405456155, ONLINE, , NO, 2719061",
        )
    ]


def test_discover_normal() -> None:
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
        ]
    )
    assert list(discover_oracle_recovery_status(section)) == [Service(item="ORCL")]


def test_discover_skips_failure_row() -> None:
    assert not list(discover_oracle_recovery_status(parse_oracle_recovery_status(_FAILURE)))


def test_check_missing_goes_stale() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_oracle_recovery_status("ORCL", {}, parse_oracle_recovery_status([])))


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
