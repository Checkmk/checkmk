#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple

import pytest

from tests.testlib import Check

from cmk.base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

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
def test_oracle_jobs_discovery_error(info) -> None:
    check = Check("oracle_jobs")
    assert list(check.run_discovery(info)) == []


@pytest.mark.parametrize(
    "info",
    [
        _broken_info,
    ],
)
def test_oracle_jobs_check_error(info) -> None:
    check = Check("oracle_jobs")
    with pytest.raises(MKCounterWrapped):
        check.run_check("DB19.SYS.JOB1", {}, info)


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
    assert list(Check("oracle_jobs").run_discovery(_STRING_TABLE_CDB_NONCDB)) == [
        (
            "CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB",
            {},
        ),
        (
            "NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB",
            {},
        ),
    ]


@pytest.mark.parametrize(
    "item, result",
    [
        pytest.param(
            "CDB.CDB$ROOT.SYS.AUTO_SPACE_ADVISOR_JOB",
            (
                0,
                "Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 15-JUN-21 01.01.01.143871 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)",
                [
                    ("duration", 0),
                ],
            ),
            id="cdb",
        ),
        pytest.param(
            "NONCDB.SYS.AUTO_SPACE_ADVISOR_JOB",
            (
                1,
                "Job-State: SCHEDULED, Enabled: Yes, Last Duration: 16 minutes 35 seconds, Next Run: 16-JUN-21 01.01.01.143871 AM +00:00,  no log information found(!)",
                [
                    ("duration", 995),
                ],
            ),
            id="noncdb",
        ),
    ],
)
def test_check_cdb_noncdb(
    item: str,
    result: Tuple[int, str, Sequence[Tuple[str, int]]],
) -> None:
    assert (
        Check("oracle_jobs").run_check(
            item,
            {
                "disabled": False,
                "status_missing_jobs": 2,
                "missinglog": 1,
            },
            _STRING_TABLE_CDB_NONCDB,
        )
        == result
    )
