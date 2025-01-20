#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.mssql.agent_based.mssql_jobs import (
    check_mssql_jobs,
    discover_mssql_jobs,
    parse_mssql_jobs,
)

INFO1 = [
    ["MSSQLSERVER"],
    [
        "{2C32E575-3C76-48E0-9E04-43BD2A15B2E1}",
        "teststsssss",
        "1",
        "",
        "",
        "5",
        "",
        "0",
        "0",
        "0",
        "",
        "2021-02-08 07:38:50",
    ],
]

INFO2 = [
    [
        "MSSQLSERVER",
    ],
    [
        "{CB09DA64-FBBD-46A0-9CD4-02D609249DE4}",
        "täglich 00:03",
        "1",
        "20200929",
        "300",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 55 (täglich 00:03).  The last step to run was step 2 (Tagesstatistik Listentool).",
        "20200928",
        "300",
        "35",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{DD63E68D-61FF-42CB-9986-0B00276611EE}",
        "4x Täglich Infomanagement",
        "1",
        "20200929",
        "63333",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 126 (4x Täglich ab 06:30 Uhr).  The last step to run was step 1 (auto_importAll).",
        "20200928",
        "123333",
        "745",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{E185714E-1231-4A02-88E5-21D521DE6A61}",
        "Wartung Stündlich",
        "1",
        "20200928",
        "161500",
        "0",
        "The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Stündlich.",
        "20200928",
        "151500",
        "9",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{76F94409-DDB4-4F9B-9AE2-3AF23AF46C48}",
        "1x Täglich",
        "1",
        "20200929",
        "32000",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 43 (Mo-Sa 03:20).  The last step to run was step 18 (Abgleich MAV).",
        "20200928",
        "32000",
        "10806",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{4B9D1121-FDEF-4CA5-A202-4ED8B0421230}",
        "aller 2h",
        "1",
        "20200928",
        "170500",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 48 (Mo-Sa 07:00 aller 2h).  The last step to run was step 2 (Magicinfo_Device_IP).",
        "20200928",
        "150501",
        "1245",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{11E5BEA3-6925-45F7-B67B-5B954F11153A}",
        "Wartung Täglich",
        "1",
        "20200929",
        "14500",
        "0",
        "The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Täglich.",
        "20200928",
        "14500",
        "341",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{783F8CB4-A09A-409A-BFBF-6822589DFA50}",
        "1x Täglich 6:00 Uhr",
        "1",
        "20200929",
        "60101",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 84 (Mo-So 6:00 Uhr).  The last step to run was step 2 (C2C_Export_OptIn).",
        "20200928",
        "60101",
        "43",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{A58A7683-E8CF-446B-AED7-6A60D8E29FE0}",
        "1x Täglich Infomanagement",
        "1",
        "20200929",
        "21700",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 61 (Mo-So 02:17).  The last step to run was step 1 (Quali AUTO MAIN).",
        "20200928",
        "21700",
        "3628",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{32267254-2240-474F-92D1-806FDBBC036E}",
        "Sonntag",
        "1",
        "20201004",
        "73400",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 60 (Sonntag).  The last step to run was step 1 (LdapImportActiveDirectory).",
        "20200927",
        "73400",
        "134",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{03013FF0-175C-4492-9C03-89AD3A05926C}",
        "SSIS Server Maintenance Job",
        "1",
        "20200929",
        "0",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 10 (SSISDB Scheduler).  The last step to run was step 2 (SSIS Server Max Version Per Project Maintenance).",
        "20200928",
        "0",
        "2",
        "0",
        "2020-09-28 15:37:36",
    ],
    [
        "{000B84B2-F29F-422A-8C89-BFE84696918F}",
        "aller 1h",
        "1",
        "20200928",
        "153500",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 47 (Mo-Sa 05:30 aller 1h).  The last step to run was step 4 (Outbound IBI/PIC).",
        "20200928",
        "153500",
        "45",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{FD3904A7-A6A3-48A2-B5C7-C6AFAE646966}",
        "1 x täglich 01:00 Uhr",
        "1",
        "20200929",
        "10000",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 261 (täglich 01:00 Uhr).  The last step to run was step 2 (C2C Import AIC).",
        "20200928",
        "10000",
        "43",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{99B511D3-A808-4B50-8C57-C962B4E5DA55}",
        "1x täglich ttCall",
        "0",
        "20200929",
        "53000",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 173 (ttCall).  The last step to run was step 1 (Projekt Vorausverfügung-Veraltete Daten disablen).",
        "20200928",
        "53000",
        "1",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{C31ED308-A554-40A0-B10A-CB06988FEDA5}",
        "aller 15 min",
        "1",
        "20200928",
        "153005",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 77 (CMS Import).  The last step to run was step 1 (CMS Intervall Import).",
        "20200928",
        "153005",
        "34",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{54DBA242-E5AA-4A45-8ABB-D166C1493170}",
        "aller 5 min",
        "1",
        "20200928",
        "152934",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 255 (aller 5 min in GZ).  The last step to run was step 1 (CMS hagent).",
        "20200928",
        "153434",
        "6",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}",
        "SSRS BO-Tool Report DL",
        "1",
        "20200928",
        "175600",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).",
        "20200928",
        "145600",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}",
        "SSRS BO-Tool Report DL",
        "1",
        "20200928",
        "195600",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).",
        "20200928",
        "145600",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}",
        "SSRS BO-Tool Report DL",
        "1",
        "20200928",
        "215600",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).",
        "20200928",
        "145600",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}",
        "SSRS BO-Tool Report DL",
        "1",
        "20200929",
        "115600",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).",
        "20200928",
        "145600",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}",
        "SSRS BO-Tool Report DL",
        "1",
        "20200929",
        "145600",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).",
        "20200928",
        "145600",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{3E0CEFB9-DCCD-43E7-BF86-F1406AB5E318}",
        "SSRS AIC Report DL",
        "1",
        "20200928",
        "160000",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 16 (Mo-So 07-23 Uhr).  The last step to run was step 1 (SSRS AIC Report DL).",
        "20200928",
        "150000",
        "0",
        "1",
        "2020-09-28 15:37:36",
    ],
    [
        "{35572CF3-551F-4216-84E7-FCEC2A2FE508}",
        "14 Uhr",
        "1",
        "20200929",
        "140500",
        "1",
        "The job succeeded.  The Job was invoked by Schedule 46 (Mo-So 14:00).  The last step to run was step 2 (Aktivitaeten).",
        "20200928",
        "140500",
        "758",
        "1",
        "2020-09-28 15:37:36",
    ],
]


def test_discovery1() -> None:
    assert list(discover_mssql_jobs(parse_mssql_jobs(INFO1))) == [
        Service(item="teststsssss"),
    ]


def test_discovery2() -> None:
    assert list(discover_mssql_jobs(parse_mssql_jobs(INFO2))) == [
        Service(item="täglich 00:03"),
        Service(item="4x Täglich Infomanagement"),
        Service(item="Wartung Stündlich"),
        Service(item="1x Täglich"),
        Service(item="aller 2h"),
        Service(item="Wartung Täglich"),
        Service(item="1x Täglich 6:00 Uhr"),
        Service(item="1x Täglich Infomanagement"),
        Service(item="Sonntag"),
        Service(item="SSIS Server Maintenance Job"),
        Service(item="aller 1h"),
        Service(item="1 x täglich 01:00 Uhr"),
        Service(item="1x täglich ttCall"),
        Service(item="aller 15 min"),
        Service(item="aller 5 min"),
        Service(item="SSRS BO-Tool Report DL"),
        Service(item="SSRS AIC Report DL"),
        Service(item="14 Uhr"),
    ]


def test_check1() -> None:
    assert list(
        check_mssql_jobs(
            "teststsssss",
            {
                "consider_job_status": "ignore",
                "status_disabled_jobs": 0,
                "status_missing_jobs": 2,
                "run_duration": None,
            },
            parse_mssql_jobs(INFO1),
        )
    ) == [
        Result(state=State.OK, summary="Last duration: 0 seconds"),
        Metric("database_job_duration", 0.0),
        Result(state=State.OK, summary="MSSQL status: Unknown"),
        Result(state=State.OK, summary="Last run: N/A"),
        Result(state=State.OK, summary="Schedule is disabled"),
        Result(state=State.OK, notice="Outcome message: "),
    ]


def test_check2() -> None:
    assert list(
        check_mssql_jobs(
            "Wartung Stündlich",
            {
                "consider_job_status": "consider",
                "status_disabled_jobs": 0,
                "status_missing_jobs": 2,
                "run_duration": (1800, 2400),
            },
            parse_mssql_jobs(INFO2),
        )
    ) == [
        Result(state=State.OK, summary="Last duration: 9 seconds"),
        Metric("database_job_duration", 9.0, levels=(1800.0, 2400.0)),
        Result(state=State.CRIT, summary="MSSQL status: Fail"),
        Result(state=State.OK, summary="Last run: 2020-09-28 15:15:00"),
        Result(state=State.OK, summary="Next run: 2020-09-28 16:15:00"),
        Result(
            state=State.OK,
            notice=(
                "Outcome message: The job failed.  JobManager tried to run a non-existent"
                " step (3) for job Wartung Stündlich."
            ),
        ),
    ]


def test_check3() -> None:
    assert list(
        check_mssql_jobs(
            "aller 2h",
            {
                "consider_job_status": "ignore",
                "status_disabled_jobs": 0,
                "status_missing_jobs": 2,
                "run_duration": (1800, 2400),
            },
            parse_mssql_jobs(INFO2),
        )
    ) == [
        Result(state=State.OK, summary="Last duration: 12 minutes 45 seconds"),
        Metric("database_job_duration", 765.0, levels=(1800.0, 2400.0)),
        Result(state=State.OK, summary="MSSQL status: Succeed"),
        Result(state=State.OK, summary="Last run: 2020-09-28 15:05:01"),
        Result(state=State.OK, summary="Next run: 2020-09-28 17:05:00"),
        Result(
            state=State.OK,
            notice=(
                "Outcome message: The job succeeded.  The Job was invoked by Schedule 48 (Mo-"
                "Sa 07:00 aller 2h).  The last step to run was step 2 (Magicinfo_Device_IP)."
            ),
        ),
    ]


@pytest.mark.parametrize(
    "string_table, item, params, expected_result",
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
                Result(state=State.OK, summary="Last duration: 0 seconds"),
                Metric("database_job_duration", 0.0),
                Result(state=State.OK, summary="MSSQL status: Unknown"),
                Result(state=State.OK, summary="Last run: 2022-12-19 04:00:00"),
                Result(state=State.OK, summary="Job is disabled"),
                Result(state=State.OK, notice="Outcome message: An error occurred."),
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
                Result(state=State.OK, summary="Last duration: 0 seconds"),
                Metric("database_job_duration", 0.0),
                Result(state=State.UNKNOWN, summary="MSSQL status: Unknown"),
                Result(state=State.OK, summary="Last run: 2022-12-19 04:00:00"),
                Result(state=State.OK, summary="Schedule is disabled"),
                Result(state=State.OK, notice="Outcome message: An error occurred."),
            ],
            id="consider_if_enabled on, job enabled",
        ),
    ],
)
def test_check_mssql_jobs(
    string_table: StringTable,
    item: str,
    params: Mapping[str, object],
    expected_result: CheckResult,
) -> None:
    section = parse_mssql_jobs(string_table)

    assert list(check_mssql_jobs(item, params, section)) == expected_result
