#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Tuple

import pytest

from tests.testlib import Check


@pytest.mark.parametrize(
    "info, item, params, expected_result",
    [
        pytest.param(
            [
                ["MSSQLSERVER"],
                [
                    "{ABC-1234}",
                    "MyJob",
                    "0",
                    "20221226",
                    "40000",
                    "5",
                    "An error occurred.",
                    "20221219",
                    "40000",
                    "0",
                    "0",
                    "2022-12-23 08:52:50",
                ],
            ],
            "MyJob",
            {
                "consider_job_status": "consider_if_enabled",
                "status_disabled_jobs": 0,
                "status_missing_jobs": 2,
            },
            [
                (0, "Last duration: 0.00 s", [("database_job_duration", 0.0, None, None)]),
                (0, "MSSQL status: Unknown"),
                (0, "Last run: 2022-12-19 04:00:00"),
                (0, "Job is disabled"),
                (0, "\nOutcome message: An error occurred."),
            ],
            id="consider_if_enabled on, job disabled",
        ),
        pytest.param(
            [
                ["MSSQLSERVER"],
                [
                    "{ABC-1234}",
                    "MyJob",
                    "1",
                    "20221226",
                    "40000",
                    "5",
                    "An error occurred.",
                    "20221219",
                    "40000",
                    "0",
                    "0",
                    "2022-12-23 08:52:50",
                ],
            ],
            "MyJob",
            {
                "consider_job_status": "consider_if_enabled",
                "status_disabled_jobs": 0,
                "status_missing_jobs": 2,
            },
            [
                (0, "Last duration: 0.00 s", [("database_job_duration", 0.0, None, None)]),
                (3, "MSSQL status: Unknown"),
                (0, "Last run: 2022-12-19 04:00:00"),
                (0, "Schedule is disabled"),
                (0, "\nOutcome message: An error occurred."),
            ],
            id="consider_if_enabled on, job enabled",
        ),
    ],
)
def test_check_mssql_jobs(
    info: Sequence[Sequence[str]],
    item: str,
    params: Mapping[str, object],
    expected_result: Sequence[Tuple[str, int]],
) -> None:
    check = Check("mssql_jobs")
    section = check.run_parse(info)

    assert list(check.run_check(item, params, section)) == expected_result
