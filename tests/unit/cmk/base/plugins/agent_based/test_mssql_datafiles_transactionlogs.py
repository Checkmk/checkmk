#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.mssql_datafiles_transactionlogs as msdt
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.df_section import parse_df
from cmk.base.plugins.agent_based.utils.df import DfBlock

SECTION_MSSQL = msdt.parse_mssql_datafiles(
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
    "section_mssql, section_df",
    [
        (
            SECTION_MSSQL,
            parse_df(
                [
                    ["Z:\\\\", "NTFS", "31463268", "16510812", "14952456", "53%", "Z:\\\\"],
                ]
            ),
        ),
        (
            SECTION_MSSQL,
            None,
        ),
    ],
)
def test_discovery_mssql_transactionlogs(section_mssql, section_df):
    assert sorted(
        msdt.discover_mssql_transactionlogs([{}], section_mssql, section_df),
        key=lambda s: s.item or "",  # type: ignore[attr-defined]
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
    "item, section_mssql, section_df, check_results",
    [
        (
            "MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log",
            SECTION_MSSQL,
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
            SECTION_MSSQL,
            parse_df(
                [
                    ["Z:\\\\", "NTFS", "31463268", "16510812", "14952456000000", "53%", "Z:\\\\"],
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
            SECTION_MSSQL,
            parse_df(
                [
                    ["Z:\\\\", "NTFS", "31463268", "16510812", "14952456000000", "53%", "Z:\\\\"],
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
            SECTION_MSSQL,
            parse_df(
                [
                    ["Z:\\\\", "NTFS", "1", "1", "1", "53%", "Z:\\\\"],
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
def test_check_mssql_transactionlogs(item, section_mssql, section_df, check_results):
    assert (
        list(
            msdt.check_mssql_transactionlogs(
                item,
                {},
                section_mssql,
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
                    "mountpoint": "F",
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
