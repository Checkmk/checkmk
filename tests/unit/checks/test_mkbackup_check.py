#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import datetime, timedelta

import pytest

from cmk.base.legacy_checks.mkbackup import check_mkbackup

from cmk.agent_based.v1 import render
from cmk.agent_based.v1.type_defs import StringTable

from .checktestlib import Check

STATE_OK = 0
STATE_WARN = 1
STATE_CRIT = 2

pytestmark = pytest.mark.checks

info_1 = [
    ["[[[site:heute:test]]]"],
    ["{"],
    ['"bytes_per_second":', "1578215.4167199447,"],
    ['"finished":', "1511788263.410466,"],
    ['"next_schedule":', "1511874660.0,"],
    [
        '"output":',
        '"2017-11-27',
        "14:11:02",
        "---",
        "Starting",
        "backup",
        "(Check_MK-klappfel-heute-test",
        "to",
        "testtgt)",
        "---\\n2017-11-27",
        "14:11:03",
        "Verifying",
        "backup",
        "consistency\\n2017-11-27",
        "14:11:03",
        "---",
        "Backup",
        "completed",
        "(Duration:",
        "0:00:01,",
        "Size:",
        "1.80",
        "MB,",
        "IO:",
        "1.51",
        "MB/s)",
        '---\\n",',
    ],
    ['"pid":', "20963,"],
    ['"size":', "1883330,"],
    ['"started":', "1511788262.20002,"],
    ['"state":', '"finished",'],
    ['"success":', "true"],
    ["}"],
]

info_2 = [
    ["[[[site:heute:test]]]"],
    ["{"],
    ['"bytes_per_second":', "1578215.4167199447,"],
    ['"finished":', "1511788263.410466,"],
    ['"next_schedule":', "1511874660.0,"],
    [
        '"output":',
        '"2017-11-27',
        "14:11:02",
        "---",
        "Starting",
        "backup",
        "(Check_MK-klappfel-heute-test",
        "to",
        "testtgt)",
        "---\\n2017-11-27",
        "14:11:03",
        "Verifying",
        "backup",
        "consistency\\n2017-11-27",
        "14:11:03",
        "---",
        "Backup",
        "completed",
        "(Duration:",
        "0:00:01,",
        "Size:",
        "1.80",
        "MB,",
        "IO:",
        "1.51",
        "MB/s)",
        '---\\n",',
    ],
    ['"pid":', "20963,"],
    ['"size":', "1883330,"],
    ['"started":', "1511788262.20002,"],
    ['"state":', '"finished",'],
    ['"success":', "true"],
    ["}"],
    ["[[[site:heute:test2]]]"],
    ["{"],
    ['"bytes_per_second":', "0,"],
    ['"finished":', "1511788748.77112,"],
    ['"next_schedule":', "null,"],
    [
        '"output":',
        '"2017-11-27',
        "14:19:07",
        "---",
        "Starting",
        "backup",
        "(Check_MK-klappfel-heute-test2",
        "to",
        "testtgt2)",
        "---\\n2017-11-27",
        "14:19:08",
        "Verifying",
        "backup",
        "consistency\\n2017-11-27",
        "14:19:08",
        "---",
        "Backup",
        "completed",
        "(Duration:",
        "0:00:00,",
        "Size:",
        "87.07",
        "MB,",
        "IO:",
        "0.00",
        "B/s)",
        '---\\n",',
    ],
    ['"pid":', "24201,"],
    ['"size":', "91299840,"],
    ['"started":', "1511788747.898509,"],
    ['"state":', '"finished",'],
    ['"success":', "true"],
    ["}"],
]

info_3 = [
    ["[[[system:test1]]]"],
    ["{"],
    ['"bytes_per_second":', "0,"],
    ['"finished":', "1474547810.309871,"],
    ['"next_schedule":', "null,"],
    [
        '"output":',
        '"2016-09-22',
        "14:36:50",
        "---",
        "Starting",
        "backup",
        "(Check_MK_Appliance-luss028-test1",
        "to",
        "test1)",
        "---\\nFailed",
        "to",
        "create",
        "the",
        "backup",
        "directory:",
        "[Errno",
        "13]",
        "Permission",
        "denied:",
        "'/mnt/auto/DIDK7838/Anwendungen/Check_MK_Appliance-luss028-test1-incomplete'\\n\",",
    ],
    ['"pid":', "29567,"],
    ['"started":', "1474547810.30425,"],
    ['"state":', '"finished",'],
    ['"success":', "false"],
    ["}"],
]

info_4 = [
    ["[[[system:test1]]]"],
    ["{"],
    ['"bytes_per_second":', "123.45,"],
    ['"finished":', "1474547810.309871,"],
    ['"next_schedule":', "1736816400.0,"],
    [
        '"output":',
        '"2025-01-13',
        "02:00:02",
        "---",
        "Starting",
        "backup",
        "(...)---\\nAn exception occurred:\\nTraceback (most recent call last):\\n",
        "...\\nOSError:",
        "[Errno",
        "28]",
        "No",
        "space",
        "left",
        "on",
        'device\\n",',
    ],
    ['"pid":', "29567,"],
    ['"started":', "1474547810.30425,"],
    ['"state":', '"finished",'],
    ['"success":', "false,"],
    ['"size":', "null"],
    ["}"],
]

info_5 = [
    ["[[[system:test1]]]"],
    ["{"],
    ['"bytes_per_second":', "123.45,"],
    ['"finished":', "1474547810.309871,"],
    ['"next_schedule":', "1736816400.0,"],
    [
        '"output":',
        '"2025-01-13',
        "02:00:02",
        "---",
        "Starting",
        'backup",',
    ],
    ['"pid":', "29567,"],
    ['"started":', "1474547810.30425,"],
    ['"state":', '"running",'],
    ['"success":', "false,"],
    ['"size":', "null"],
    ["}"],
]


# This only tests whether the parse function crashes or not
@pytest.mark.parametrize(
    "info, expect_check_result",
    [
        pytest.param([], False, id="Empty string table"),
        pytest.param(info_1, False, id="Successful site backup"),
        pytest.param(info_2, False, id="Multiple successful site backups"),
        pytest.param(info_3, True, id="Failed system backup w/o size data"),
        pytest.param(info_4, True, id="Failed system backup w/ null size data"),
        pytest.param(info_5, True, id="Running system backup w/ null size data"),
    ],
)
def test_mkbackup_parse(info: StringTable, expect_check_result: bool) -> None:
    check = Check("mkbackup")
    parsed = check.run_parse(info)
    check_result = check.run_check("test1", {}, parsed)
    if expect_check_result:
        assert check_result is not None
        list(check_result)


def test_check_mkbackup_ok_when_started() -> None:
    started = datetime.today() - timedelta(minutes=5)
    results = list(
        check_mkbackup({"state": "started", "started": started.timestamp(), "bytes_per_second": 10})
    )

    assert results[0][0] == STATE_OK
    assert (
        results[0][1]
        == f"The job is running for 5 minutes 0 seconds since {render.datetime(started.timestamp())}"
    )


def test_check_mkbackup_ok_when_running() -> None:
    started = datetime.today() - timedelta(minutes=5)
    job_state = {"state": "running", "started": started.timestamp(), "bytes_per_second": 10}
    results = list(check_mkbackup(job_state))

    assert results[0][0] == STATE_OK
    assert (
        results[0][1]
        == f"The job is running for 5 minutes 0 seconds since {render.datetime(started.timestamp())}"
    )


def test_check_mkbackup_ok_when_finished_and_successful() -> None:
    started = datetime.today()
    finished = started + timedelta(minutes=5)
    results = list(
        check_mkbackup(
            {
                "state": "finished",
                "started": started.timestamp(),
                "finished": finished.timestamp(),
                "bytes_per_second": 10,
                "success": True,
                "next_schedule": "disabled",
            }
        )
    )
    assert (STATE_OK, "Backup completed") in results


def test_check_mkbackup_crit_when_finished_and_failed() -> None:
    started = datetime.today()
    finished = started + timedelta(minutes=5)
    results = list(
        check_mkbackup(
            {
                "state": "finished",
                "started": started.timestamp(),
                "finished": finished.timestamp(),
                "bytes_per_second": 10,
                "success": False,
                "next_schedule": "disabled",
            }
        )
    )
    assert (STATE_CRIT, "Backup failed") in results


def test_check_mkbackup_warn_when_finished_and_disabled() -> None:
    started = datetime.today()
    finished = started + timedelta(minutes=5)
    results = list(
        check_mkbackup(
            {
                "state": "finished",
                "started": started.timestamp(),
                "finished": finished.timestamp(),
                "bytes_per_second": 10,
                "success": True,
                "next_schedule": "disabled",
            }
        )
    )
    assert (STATE_WARN, "Schedule is currently disabled") in results


@pytest.mark.parametrize(
    "next_schedule",
    [
        datetime.today(),
        datetime.today() + timedelta(minutes=1),
        datetime.today() + timedelta(minutes=2),
        datetime.today() + timedelta(days=1),
        datetime.today() + timedelta(weeks=1),
    ],
)
def test_check_mkbackup_ok_when_finished_and_next_schedule_is_on_time(
    next_schedule: datetime,
) -> None:
    started = datetime.now()
    finished = started + timedelta(seconds=30)
    results = list(
        check_mkbackup(
            {
                "state": "finished",
                "started": started.timestamp(),
                "finished": finished.timestamp(),
                "bytes_per_second": 10,
                "success": True,
                "next_schedule": next_schedule.timestamp(),
            }
        )
    )
    assert (STATE_OK, f"Next run: {render.datetime(next_schedule.timestamp())}") in results


@pytest.mark.parametrize(
    "next_schedule",
    [
        datetime.today() - timedelta(minutes=2),
        datetime.today() - timedelta(minutes=3),
        datetime.today() - timedelta(days=1),
        datetime.today() - timedelta(weeks=1),
    ],
)
def test_check_mkbackup_crit_when_finished_and_next_schedule_is_late(
    next_schedule: datetime,
) -> None:
    started = datetime.today() - timedelta(days=7)
    finished = started + timedelta(seconds=30)
    results = list(
        check_mkbackup(
            {
                "state": "finished",
                "started": started.timestamp(),
                "finished": finished.timestamp(),
                "bytes_per_second": 10,
                "success": True,
                "next_schedule": next_schedule.timestamp(),
            }
        )
    )
    assert (STATE_CRIT, f"Next run: {render.datetime(next_schedule.timestamp())}") in results
