#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.base.legacy_checks.oracle_jobs import (
    check_oracle_jobs,
    inventory_oracle_jobs,
    parse_oracle_jobs,
)

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State

_broken_info = [
    [
        "DB19",
        " Debug (121): ORA-01219: database or pluggable database not open: queries allowed on fixed tables or views only",
    ]
]


@pytest.mark.parametrize(
    "info",
    [
        _broken_info,
    ],
)
def test_oracle_jobs_discovery_error(info: StringTable) -> None:
    assert not list(inventory_oracle_jobs(parse_oracle_jobs(info)))


@pytest.mark.parametrize(
    "info",
    [
        _broken_info,
    ],
)
def test_oracle_jobs_check_error(info: StringTable) -> None:
    with pytest.raises(IgnoreResultsError):
        _ = list(check_oracle_jobs("DB19.SYS.JOB1", {}, parse_oracle_jobs(info)))


_STRING_TABLE_CDB_NONCDB = [
    [
        "CDB",
        "CDB$ROOT",
        "SYS",
        "AUTO_SPACE_ADVISOR_JOB",
        "SCHEDULED",
        "0",
        "46",
        "TRUE",
        "15-JUN-21 01.01.01.143871 AM +00:00",
        "-",
        "SUCCEEDED",
    ],
    [
        "NONCDB",
        "SYS",
        "AUTO_SPACE_ADVISOR_JOB",
        "SCHEDULED",
        "995",
        "1129",
        "TRUE",
        "16-JUN-21 01.01.01.143871 AM +00:00",
        "MAINTENANCE_WINDOW_GROUP",
        "",
    ],
]


def test_discovery_cdb_noncdb() -> None:
    assert list(inventory_oracle_jobs(parse_oracle_jobs(_STRING_TABLE_CDB_NONCDB))) == [
        Service(item="CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB"),
        Service(item="NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB"),
    ]


@pytest.mark.parametrize(
    "item, result",
    [
        pytest.param(
            "CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB",
            [
                Result(
                    state=State.OK,
                    summary="Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 15-JUN-21 01.01.01.143871 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)",
                ),
                Metric("duration", 0),
            ],
            id="cdb",
        ),
        pytest.param(
            "NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB",
            [
                Result(
                    state=State.WARN,
                    summary="Job-State: SCHEDULED, Enabled: Yes, Last Duration: 16 minutes 35 seconds, Next Run: 16-JUN-21 01.01.01.143871 AM +00:00,  no log information found(!)",
                ),
                Metric("duration", 995),
            ],
            id="noncdb",
        ),
    ],
)
def test_check_cdb_noncdb(
    item: str,
    result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_oracle_jobs(
                item,
                {
                    "consider_job_status": "consider",
                    "status_missing_jobs": 2,
                    "missinglog": 1,
                },
                parse_oracle_jobs(_STRING_TABLE_CDB_NONCDB),
            )
        )
        == result
    )


INFO = [
    [
        "DB19",
        "CDB$ROOT",
        "ORACLE_OCM",
        "MGMT_STATS_CONFIG_JOB",
        "SCHEDULED",
        "0",
        "2",
        "TRUE",
        "01-JAN-20 01.01.01.312723 AM +00:00",
        "-",
        "SUCCEEDED",
    ]
]


def test_discovery() -> None:
    assert list(inventory_oracle_jobs(parse_oracle_jobs(INFO))) == [
        Service(item="DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB")
    ]


def test_check() -> None:
    assert list(
        check_oracle_jobs(
            "DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB",
            {"consider_job_status": "ignore", "status_missing_jobs": 2, "missinglog": 1},
            parse_oracle_jobs(INFO),
        )
    ) == [
        Result(
            state=State.OK,
            summary="Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 01-JAN-20 01.01.01.312723 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)",
        ),
        Metric("duration", 0),
    ]


def test_check_item_missing() -> None:
    assert list(
        check_oracle_jobs(
            "DB19.CDB$ROOT.ORACLE_OCM.MISSING",
            {"status_missing_jobs": 2},
            parse_oracle_jobs(INFO),
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Job is missing",
        )
    ]


INFO2 = [
    [
        "ORCLCDB",
        "CDB$ROOT",
        "SYS",
        "PURGE_LOG",
        "SCHEDULED",
        "6",
        "4",
        "TRUE",
        "03-DEC-19 03.00.00.421040 AM PST8PDT",
        "DAILY_PURGE_SCHEDULE",
        "SUCCEEDED",
    ],
    [
        "ORCLCDB",
        "CDB$ROOT",
        "SYS",
        "CLEANUP_ONLINE_PMO",
        "SCHEDULED",
        "0",
        "68",
        "TRUE",
        "02-DEC-19 09.15.07.529970 AM -07:00",
        "-",
        "",
    ],
]


def test_discovery2() -> None:
    assert list(inventory_oracle_jobs(parse_oracle_jobs(INFO2))) == [
        Service(item="ORCLCDB.CDB$ROOT.SYS.PURGE_LOG"),
        Service(item="ORCLCDB.CDB$ROOT.SYS.CLEANUP_ONLINE_PMO"),
    ]


def test_check2() -> None:
    assert list(
        check_oracle_jobs(
            "ORCLCDB.CDB$ROOT.SYS.CLEANUP_ONLINE_PMO",
            {"consider_job_status": "ignore", "status_missing_jobs": 2, "missinglog": 1},
            parse_oracle_jobs(INFO2),
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 02-DEC-19 09.15.07.529970 AM -07:00,  no log information found(!)",
        ),
        Metric("duration", 0),
    ]


def test_check2_last_run_succeded() -> None:
    assert list(
        check_oracle_jobs(
            "ORCLCDB.CDB$ROOT.SYS.PURGE_LOG",
            {"consider_job_status": "ignore", "status_missing_jobs": 2, "missinglog": 1},
            parse_oracle_jobs(INFO2),
        )
    ) == [
        Result(
            state=State.OK,
            summary="Job-State: SCHEDULED, Enabled: Yes, Last Duration: 6 seconds, Next Run: 03-DEC-19 03.00.00.421040 AM PST8PDT, Last Run Status: SUCCEEDED (ignored disabled Job)",
        ),
        Metric("duration", 6),
    ]
