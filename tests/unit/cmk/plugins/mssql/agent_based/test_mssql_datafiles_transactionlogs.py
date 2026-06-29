#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import lru_cache
from typing import NamedTuple

import pytest

import cmk.plugins.mssql.agent_based.mssql_datafiles_transactionlogs as msdt
from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.df_section import parse_df
from cmk.plugins.lib.df import BlocksSubsection, DfBlock, InodesSubsection


@lru_cache
def section_mssql() -> msdt.SectionDatafiles:
    return msdt.parse_mssql_datafiles(
        [
            [
                "MSSQL46",
                "CorreLog_Report_T",
                "CorreLog_Report_T_log",
                "Z:\\mypath\\CorreLog_Report_T_log.ldf",
                "2097152",
                "256",
                "16",
                "0",
            ],
            [
                "MSSQL46",
                "DASH_CONFIG_T",
                "DASH_CONFIG_T_log",
                "Z:\\mypath\\DASH_CONFIG_T_log.ldf",
                "2097152",
                "256",
                "1",
                "0",
            ],
            ["MSSQL46", "master", "mastlog", "Z:\\mypath\\mastlog.ldf", "0", "1", "0", "1"],
            ["MSSQL46", "model", "modellog", "Z:\\mypath\\modellog.ldf", "0", "34", "32", "1"],
            ["MSSQL46", "msdb", "MSDBLog", "Z:\\mypath\\MSDBLog.ldf", "2097152", "17", "3", "0"],
            [
                "MSSQL46",
                "NOC_ALARM_T",
                "NOC_ALARM_T_log",
                "Z:\\mypath\\NOC_ALARM_T_log.ldf",
                "2097152",
                "256",
                "8",
                "0",
            ],
            [
                "MSSQL46",
                "NOC_CONFIG_T",
                "NOC_CONFIG_T_log",
                "Z:\\mypath\\NOC_CONFIG_T_log.ldf",
                "2097152",
                "768",
                "31",
                "0",
            ],
            ["MSSQL46", "tempdb", "templog", "Z:\\mypath\\templog.ldf", "0", "160", "55", "1"],
            [
                "MSSQL46",
                "test_autoclose",
                "test_autoclose_log",
                "Z:\\mypath\\test_autoclose_log.ldf",
                "2097152",
                "32",
                "1",
                "0",
            ],
        ]
    )


@pytest.mark.parametrize(
    "section_df",
    [
        (
            parse_df(
                [
                    ["Z:\\", "NTFS", "31463268", "16510812", "14952456", "53%", "Z:\\"],
                ]
            ),
        ),
        (None,),
    ],
)
def test_discovery_mssql_transactionlogs(
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> None:
    assert sorted(
        msdt.discover_mssql_transactionlogs([{}], section_mssql(), section_df),
        key=lambda s: s.item or "",
    ) == [
        Service(item="MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log"),
        Service(item="MSSQL46.DASH_CONFIG_T.DASH_CONFIG_T_log"),
        Service(item="MSSQL46.NOC_ALARM_T.NOC_ALARM_T_log"),
        Service(item="MSSQL46.NOC_CONFIG_T.NOC_CONFIG_T_log"),
        Service(item="MSSQL46.master.mastlog"),
        Service(item="MSSQL46.model.modellog"),
        Service(item="MSSQL46.msdb.MSDBLog"),
        Service(item="MSSQL46.tempdb.templog"),
        Service(item="MSSQL46.test_autoclose.test_autoclose_log"),
    ]


@pytest.mark.parametrize(
    "item, section_df, check_results",
    [
        (
            "MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log",
            None,
            [
                Result(
                    state=State.OK,
                    summary="Used: 16.0 MiB",
                ),
                Metric("data_size", 16777216.0, boundaries=(0, 2199023255552.0)),
                Result(
                    state=State.OK,
                    summary="Allocated used: 16.0 MiB",
                ),
                Result(
                    state=State.OK,
                    summary="Allocated: 256 MiB",
                ),
                Metric("allocated_size", 268435456.0, boundaries=(0, 2199023255552.0)),
                Result(
                    state=State.OK,
                    summary="Maximum size: 2.00 TiB",  # no filesystem information -> revert to configured max size
                ),
            ],
        ),
        (
            "MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log",
            parse_df(
                [
                    ["Z:\\", "NTFS", "31463268", "16510812", "14952456000000", "53%", "Z:\\"],
                ]
            ),
            [
                Result(
                    state=State.OK,
                    summary="Used: 16.0 MiB",
                ),
                Metric("data_size", 16777216.0, boundaries=(0, 2199023255552.0)),
                Result(
                    state=State.OK,
                    summary="Allocated used: 16.0 MiB",
                ),
                Result(
                    state=State.OK,
                    summary="Allocated: 256 MiB",
                ),
                Metric("allocated_size", 268435456.0, boundaries=(0, 2199023255552.0)),
                Result(
                    state=State.OK,
                    summary="Maximum size: 2.00 TiB",  # huge filesystem but not unlimited
                ),
            ],
        ),
        (
            "MSSQL46.master.mastlog",
            parse_df(
                [
                    ["Z:\\", "NTFS", "31463268", "16510812", "14952456000000", "53%", "Z:\\"],
                ]
            ),
            [
                Result(
                    state=State.OK,
                    summary="Used: 0 B",
                ),
                Metric("data_size", 0.0, boundaries=(0, 1.5311314944e16)),
                Result(
                    state=State.OK,
                    summary="Allocated used: 0 B",
                ),
                Result(
                    state=State.OK,
                    summary="Allocated: 1.00 MiB",
                ),
                Metric("allocated_size", 1048576.0, boundaries=(0, 1.5311314944e16)),
                Result(
                    state=State.OK,
                    summary="Maximum size: 13.6 PiB",  # huge filesystem and unlimited
                ),
            ],
        ),
        (
            "MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log",
            parse_df(
                [
                    ["Z:\\", "NTFS", "1", "1", "1", "53%", "Z:\\"],
                ]
            ),
            [
                Result(
                    state=State.OK,
                    summary="Used: 16.0 MiB",
                ),
                Metric("data_size", 16777216.0, boundaries=(0, 16778240.0)),
                Result(
                    state=State.OK,
                    summary="Allocated used: 16.0 MiB",
                ),
                Result(
                    state=State.OK,
                    summary="Allocated: 256 MiB",
                ),
                Metric("allocated_size", 268435456.0, boundaries=(0, 16778240.0)),
                Result(
                    state=State.OK,
                    summary="Maximum size: 16.0 MiB",  # filesystem smaller than log size limit
                ),
            ],
        ),
    ],
)
def test_check_mssql_transactionlogs(
    item: str,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
    check_results: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            msdt.check_mssql_transactionlogs(
                item,
                {},
                section_mssql(),
                section_df,
            )
        )
        == check_results
    )


def test_check_mssql_common_unlimited() -> None:
    assert list(
        msdt.check_mssql_common(
            "SQLEXPRESS.GIS_extern.GIS_extern_dat",
            {"used_levels": (80.0, 90.0)},
            {
                ("SQLEXPRESS", "GIS_extern", "GIS_extern_dat"): {
                    "unlimited": True,
                    "max_size": 0.0,
                    "allocated_size": 44844449792.0,
                    "used_size": 40787509248.0,
                    "mountpoint": "f:\\",
                },
            },
            (
                (
                    DfBlock(
                        device="DATA",
                        fs_type="NTFS",
                        size_mb=133101.99609375,
                        avail_mb=23038.49609375,
                        reserved_mb=0.0,
                        mountpoint="F:/",
                        uuid=None,
                    ),
                ),
                (),
            ),
        )
    ) == [
        Result(state=State.OK, summary="Used: 38.0 GiB"),
        Metric(
            "data_size",
            40787509248.0,
            levels=(51956098662.4, 58450610995.2),
            boundaries=(0.0, 64945123328.0),
        ),
        Result(state=State.OK, summary="Allocated used: 38.0 GiB"),
        Result(state=State.OK, summary="Allocated: 41.8 GiB"),
        Metric("allocated_size", 44844449792.0, boundaries=(0.0, 64945123328.0)),
        Result(state=State.OK, summary="Maximum size: 60.5 GiB"),
    ]


DF_SECTION_WITH_MULTIPLE_MPS = [
    ["System", "NTFS", "125247484", "83827900", "41419584", "67%", "C:\\"],
    ["SQL_root", "NTFS", "104724416", "31955520", "72768896", "31%", "D:\\"],
    ["NAME_data", "NTFS", "1047233920", "457569280", "589664640", "44%", "D:\\MyData\\"],
    ["NAME_logs", "NTFS", "83751872", "36375296", "47376576", "44%", "D:\\MyLogs\\"],
    ["temp", "NTFS", "10485760", "375296", "10110464", "3%", "D:\\temp\\"],
]

DATAFILE_SECTION = [
    ["NAME", "master", "master1", "D:\\MyData\\master1.mdf", "0", "124890", "124172", "1"],
    ["NAME", "master", "master2", "D:\\MyData\\master2.mdf", "0", "128890", "128172", "1"],
]


def test_check_mssql_transactionlogs_multiple_mp_single() -> None:
    assert list(
        msdt.check_mssql_transactionlogs(
            "NAME.master.master1",
            {},
            msdt.parse_mssql_datafiles(DATAFILE_SECTION),
            parse_df(DF_SECTION_WITH_MULTIPLE_MPS),
        )
    ) == [
        Result(state=State.OK, summary="Used: 121 GiB"),
        Metric("data_size", 130203779072.0, boundaries=(0.0, 734020370432.0)),
        Result(state=State.OK, summary="Allocated used: 121 GiB"),
        Result(state=State.OK, summary="Allocated: 122 GiB"),
        Metric("allocated_size", 130956656640.0, boundaries=(0.0, 734020370432.0)),
        Result(state=State.OK, summary="Maximum size: 684 GiB"),
    ]


def test_check_mssql_transactionlogs_multiple_mp_summary() -> None:
    assert list(
        msdt.check_mssql_transactionlogs(
            "NAME.master",
            {},
            msdt.parse_mssql_datafiles(DATAFILE_SECTION),
            parse_df(DF_SECTION_WITH_MULTIPLE_MPS),
        )
    ) == [
        Result(state=State.OK, summary="Used: 246 GiB"),
        Metric("data_size", 264601862144.0, boundaries=(0.0, 868418453504.0)),
        Result(state=State.OK, summary="Allocated used: 246 GiB"),
        Result(state=State.OK, summary="Allocated: 248 GiB"),
        Metric("allocated_size", 266107617280.0, boundaries=(0.0, 868418453504.0)),
        Result(state=State.OK, summary="Maximum size: 809 GiB"),
    ]


SUP29484_DF = [
    ["sys", "NTFS", "125315068", "35448632", "89866436", "29%", "C:\\"],
    ["user", "NTFS", "52425724", "26347860", "26077864", "51%", "D:\\"],
    ["user2", "NTFS", "838854592", "619967168", "218887424", "74%", "E:\\"],
    ["user3", "NTFS", "524284924", "263515944", "260768980", "51%", "F:\\"],
    ["user4", "NTFS", "52425664", "4295936", "48129728", "9%", "G:\\"],
    ["user5", "NTFS", "52425664", "4295936", "48129728", "9%", "H:\\"],
    ["user6", "NTFS", "52425724", "1151300", "51274424", "3%", "I:\\"],
]

SUP29484_MSSQL_DATAFILES = [
    [
        "MSSQLSERVER",
        "ppppppppppppppppp",
        "ppppppppppppppppp_1",
        r"E:\MSSQL_Data\ppppppppppppppppp.mdf",
        "32768",
        "32768",
        "28437",
        "0",
    ],
    [
        "MSSQLSERVER",
        "ppppppppppppppppp",
        "ppppppppppppppppp_2",
        r"E:\MSSQL_Data\ppppppppppppppppp_2.ndf",
        "32768",
        "32768",
        "28251",
        "0",
    ],
    [
        "MSSQLSERVER",
        "ppppppppppppppppp",
        "ppppppppppppppppp_3",
        r"E:\MSSQL_Data\ppppppppppppppppp_3.ndf",
        "32768",
        "32768",
        "27473",
        "0",
    ],
    [
        "MSSQLSERVER",
        "ppppppppppppppppp",
        "ppppppppppppppppp_4",
        r"E:\MSSQL_Data\ppppppppppppppppp_4.ndf",
        "32768",
        "23552",
        "20990",
        "0",
    ],
    [
        "MSSQLSERVER",
        "ppppppppppppppppp",
        "ppppppppppppppppp_5",
        r"E:\MSSQL_Data\ppppppppppppppppp_5.ndf",
        "10240",
        "1024",
        "647",
        "0",
    ],
]


def test_datafile_usage_unlimited_is_evaluated_per_file() -> None:
    limited: msdt.MSSQLInstanceData = {
        "unlimited": False,
        "max_size": 10,
        "allocated_size": 3,
        "used_size": 7,
        "mountpoint": "x:\\limited.mdf",
    }
    unlimited: msdt.MSSQLInstanceData = {
        "unlimited": True,
        "max_size": 0,
        "allocated_size": 4,
        "used_size": 6,
        "mountpoint": "y:\\unlimited.ldf",
    }
    free_space_per_mountpoint = {"x:/": 1000, "y:/": 1000}

    unlimited_second = msdt._datafile_usage([limited, unlimited], free_space_per_mountpoint)
    unlimited_first = msdt._datafile_usage([unlimited, limited], free_space_per_mountpoint)

    assert unlimited_second.max == unlimited_first.max == 10 + 1006
    assert unlimited_first.used == unlimited_second.used == 7 + 6
    assert unlimited_first.allocated == unlimited_second.allocated == 3 + 4


def test_datafile_usage_no_filesystem_info_dedup_poisons_repeated_files() -> None:
    first: msdt.MSSQLInstanceData = {
        "unlimited": False,
        "max_size": 100,
        "allocated_size": 50,
        "used_size": 7,
        "mountpoint": "z:\\data\\first.mdf",
    }
    second: msdt.MSSQLInstanceData = {
        "unlimited": False,
        "max_size": 200,
        "allocated_size": 60,
        "used_size": 8,
        "mountpoint": "z:\\data\\second.mdf",
    }

    usage = msdt._datafile_usage([first, second], {})

    assert usage.max == 100 + 8  # THIS IS A BUG! should be 100 + 200


class _Scenario(NamedTuple):
    unlimited: bool
    max_size: float | None
    used_size: float
    allocated_size: float
    filesystem_free: float | None
    expected_max: float


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            _Scenario(
                unlimited=False,
                max_size=100,
                used_size=7,
                allocated_size=50,
                filesystem_free=None,
                expected_max=100,
            ),
            id="no-df-limited-uses-configured-max",
        ),
        pytest.param(
            _Scenario(
                unlimited=False,
                max_size=None,
                used_size=7,
                allocated_size=50,
                filesystem_free=None,
                expected_max=0,
            ),
            id="no-df-no-configured-max",
        ),
        pytest.param(
            _Scenario(
                unlimited=True,
                max_size=None,
                used_size=7,
                allocated_size=50,
                filesystem_free=None,
                expected_max=0,
            ),
            id="no-df-unlimited-still-zero",
        ),
        pytest.param(
            _Scenario(
                unlimited=True,
                max_size=100,
                used_size=7,
                allocated_size=50,
                filesystem_free=1000,
                expected_max=1007,
            ),
            id="df-unlimited-uses-free-plus-used",
        ),
        pytest.param(
            _Scenario(
                unlimited=False,
                max_size=100,
                used_size=7,
                allocated_size=50,
                filesystem_free=1000,
                expected_max=100,
            ),
            id="df-limited-capped-by-configured-max",
        ),
        pytest.param(
            _Scenario(
                unlimited=False,
                max_size=100000,
                used_size=7,
                allocated_size=50,
                filesystem_free=10,
                expected_max=17,  # THIS IS A BUG! it should be 100000
            ),
            id="df-limited-capped-by-filesystem",
        ),
    ],
)
def test_effective_max_size_paths(scenario: _Scenario) -> None:
    instance: msdt.MSSQLInstanceData = {
        "unlimited": scenario.unlimited,
        "max_size": scenario.max_size,
        "allocated_size": scenario.allocated_size,
        "used_size": scenario.used_size,
        "mountpoint": "z:\\data\\file.mdf",
    }
    mountpoints = {} if scenario.filesystem_free is None else {"z:/": scenario.filesystem_free}

    assert msdt._datafile_usage([instance], mountpoints).max == scenario.expected_max


def test_check_mssql_transactionlogs_multiple_mp_summary_SUP29484() -> None:
    assert list(
        msdt.check_mssql_transactionlogs(
            "MSSQLSERVER.ppppppppppppppppp",
            {},
            msdt.parse_mssql_datafiles(SUP29484_MSSQL_DATAFILES),
            parse_df(SUP29484_DF),
        )
    ) == [
        Result(state=State.OK, summary="Used: 103 GiB"),
        Metric("data_size", 110937243648.0, boundaries=(0.0, 115478626304.0)),
        Result(state=State.OK, summary="Allocated used: 103 GiB"),
        Result(state=State.OK, summary="Allocated: 120 GiB"),
        Metric("allocated_size", 128849018880.0, boundaries=(0.0, 115478626304.0)),
        Result(
            state=State.OK, summary="Maximum size: 108 GiB"
        ),  # THIS IS A BUG! should be 138 GiB, can not be smaller as allocated?!
    ]
