#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

import cmk.base.plugins.agent_based.oracle_asm_diskgroup as asm
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResults, Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

NOW_SIMULATED = 581792400, "UTC"

ITEM = "DISK_GROUP"
SECTION_OLD_MOUNTED = asm.Section(
    diskgroups={
        ITEM: asm.Diskgroup(
            dgstate="MOUNTED",
            dgtype="NORMAL",
            free_mb=4610314,
            offline_disks=0,
            req_mir_free_mb=63320,
            total_mb=5242880,
            voting_files="N",
            fail_groups=[],
        )
    }
)
SECTION_UNKNOWN_ITEM = asm.Section(diskgroups={"UNKNOWN": SECTION_OLD_MOUNTED.diskgroups[ITEM]})

SECTION_OLD_DISMOUNTED = asm.Section(
    diskgroups={
        ITEM: asm.Diskgroup(
            dgstate="DISMOUNTED",
            dgtype=None,
            free_mb=0,
            offline_disks=0,
            req_mir_free_mb=0,
            total_mb=0,
            voting_files="N",
            fail_groups=[],
        )
    }
)

SECTION_DISMOUNTED = asm.Section(
    diskgroups={
        ITEM: asm.Diskgroup(
            dgstate="DISMOUNTED",
            dgtype=None,
            total_mb=None,
            free_mb=None,
            req_mir_free_mb=0,
            offline_disks=0,
            voting_files="",
            fail_groups=[],
        )
    }
)

SECTION_CLUTTERED_WITH_DEPREACTED_AGENT_OUTPUT = asm.Section(
    found_deprecated_agent_output=True,
    diskgroups={
        ITEM: asm.Diskgroup(
            dgstate="DISMOUNTED",
            dgtype=None,
            free_mb=0,
            offline_disks=0,
            req_mir_free_mb=0,
            total_mb=0,
            voting_files="N",
            fail_groups=[],
        )
    },
)

SECTION_WITH_FG = asm.Section(
    diskgroups={
        ITEM: asm.Diskgroup(
            dgstate="MOUNTED",
            dgtype="EXTERN",
            fail_groups=[
                asm.Failgroup(
                    fg_disks=1,
                    fg_free_mb=489148,
                    fg_min_repair_time=8640000,
                    fg_name="DATA_0000",
                    fg_total_mb=614400,
                    fg_type="REGULAR",
                    fg_voting_files="N",
                )
            ],
            free_mb=489148,
            offline_disks=0,
            req_mir_free_mb=0,
            total_mb=614400,
            voting_files="N",
        )
    }
)


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "%s.delta" % ITEM: [2000000, 30000000],
    }
    monkeypatch.setattr(asm, "get_value_store", lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([[]], asm.Section({})),
        (
            [
                [
                    "UNKNOWN-STATE",
                    "NORMAL",
                    "N",
                    "512",
                    "4096",
                    "1048576",
                    "5242880",
                    "4610314",
                    "63320",
                    "2273497",
                    "0",
                    "N",
                    "%s/" % ITEM,
                ]
            ],
            asm.Section(diskgroups={}),
        ),
        (
            [
                [
                    "MOUNTED",
                    "NORMAL",
                    "N",
                    "512",
                    "4096",
                    "1048576",
                    "5242880",
                    "4610314",
                    "63320",
                    "2273497",
                    "0",
                    "N",
                    "%s/" % ITEM,
                ]
            ],
            SECTION_OLD_MOUNTED,
        ),
        (
            [["DISMOUNTED", "N", "0", "4096", "0", "0", "0", "0", "0", "0", "N", "%s/" % ITEM]],
            SECTION_OLD_DISMOUNTED,
        ),
        (
            [
                [
                    "MOUNTED",
                    "EXTERN",
                    "%s/" % ITEM,
                    "4096",
                    "4194304",
                    "0",
                    "614400",
                    "489148",
                    "DATA_0000",
                    "N",
                    "REGULAR",
                    "0",
                    "8640000",
                    "1",
                ]
            ],
            SECTION_WITH_FG,
        ),
        (
            [["DISMOUNTED", "", "%s/" % ITEM, "0", "0", "0", "", "", "", "", "", "0", "", "1"]],
            SECTION_DISMOUNTED,
        ),
        (
            [
                [
                    "MOUNTED",
                    "NORMAL",
                    "N",
                    "512",
                    "512",
                    "4096",
                    "4194304",
                    "5734400",
                    "693184",
                    "409600",
                    "141792",
                    "0",
                    "N",
                    "DATAC1/",
                ]
            ],
            asm.Section({}, found_deprecated_agent_output=True),
        ),
    ],
)
def test_parse(string_table, expected) -> None:
    parsed_section = asm.parse_oracle_asm_diskgroup(string_table)
    assert parsed_section == expected


@pytest.mark.parametrize(
    "section, expected",
    [
        (asm.Section({}), []),
        (
            asm.Section(
                {
                    ITEM: asm.Diskgroup(
                        dgstate="UNKNOWN-DG-STATE",
                        dgtype=None,
                        total_mb=0,
                        free_mb=0,
                        req_mir_free_mb=0,
                        offline_disks=0,
                        voting_files="foo",
                        fail_groups=[],
                    )
                }
            ),
            [],
        ),
        (SECTION_OLD_MOUNTED, [Service(item=ITEM)]),
        (SECTION_OLD_DISMOUNTED, [Service(item=ITEM)]),
    ],
)
def test_discovery(section, expected) -> None:
    yielded_services = list(asm.discovery_oracle_asm_diskgroup(section))
    assert yielded_services == expected


@pytest.mark.parametrize(
    "section, params, expected",
    [
        (
            SECTION_UNKNOWN_ITEM,
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [(IgnoreResults("Diskgroup %s not found" % ITEM))],
        ),
        (
            SECTION_OLD_DISMOUNTED,
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [Result(state=state.CRIT, summary="Diskgroup dismounted")],
        ),
        (
            SECTION_CLUTTERED_WITH_DEPREACTED_AGENT_OUTPUT,
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Result(
                    state=state.WARN,
                    summary="The deprecated Oracle Agent Plugin "
                    "'mk_oracle_asm' from Checkmk Version 1.2.6 is "
                    "still executed on this host. "
                    "The section 'oracle_asm_diskgroup' is now "
                    "generated by the plugin 'mk_oracle'. "
                    "Please remove the deprecated Plugin",
                ),
                Result(state=state.CRIT, summary="Diskgroup dismounted"),
            ],
        ),
        (
            SECTION_OLD_MOUNTED,
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Metric(
                    "fs_used",
                    316283.0,
                    levels=(2097152.0, 2359296.0),
                    boundaries=(0.0, 2621440.0),
                ),
                Metric(
                    "fs_size",
                    2621440.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    12.065238952636719,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=state.OK, summary="12.07% used (309 GiB of 2.50 TiB)"),
                Metric("growth", -4423.433540694911),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -4.32 GiB"),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -0.17%"),
                Metric(
                    "trend",
                    -4423.433540694911,
                    levels=(None, None),
                    boundaries=(0.0, 109226.66666666667),
                ),
                Result(
                    state=state.OK,
                    summary="normal redundancy, old plugin data, possible wrong used and free space",
                ),
            ],
        ),
        (
            SECTION_WITH_FG,
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Metric(
                    "fs_used",
                    125252.0,
                    levels=(491520.0, 552960.0),
                    boundaries=(0.0, 614400.0),
                ),
                Metric(
                    "fs_size",
                    614400.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    20.386067708333332,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=state.OK, summary="20.39% used (122 of 600 GiB)"),
                Metric("growth", -4451.90076172092),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -4.35 GiB"),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -0.72%"),
                Metric("trend", -4451.90076172092, boundaries=(0.0, 25600.0)),
                Result(state=state.OK, summary="extern redundancy, 1 disks"),
            ],
        ),
        (
            SECTION_WITH_FG,
            {
                "req_mir_free": True,  # Ignore Requirre mirror free space in DG
            },
            [
                Metric(
                    "fs_used",
                    125252.0,
                    levels=(491520.0, 552960.0),
                    boundaries=(0.0, 614400.0),
                ),
                Metric(
                    "fs_size",
                    614400.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    20.386067708333332,
                    levels=(80.0, 90.0),
                    boundaries=(0, 100.0),
                ),
                Result(state=state.OK, summary="20.39% used (122 of 600 GiB)"),
                Metric("growth", -4451.90076172092),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -4.35 GiB"),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -0.72%"),
                Metric(
                    "trend",
                    -4451.90076172092,
                    boundaries=(0.0, 25600.0),
                ),
                Result(
                    state=state.OK,
                    summary="extern redundancy, 1 disks, required mirror free space used",
                ),
            ],
        ),
    ],
)
def test_check(value_store_patch, section, params, expected) -> None:
    with on_time(*NOW_SIMULATED):

        assert expected == list(asm.check_oracle_asm_diskgroup(ITEM, params, section))


@pytest.mark.parametrize(
    "section, params, expected",
    [
        (
            {"node1": SECTION_OLD_MOUNTED, "node2": SECTION_WITH_FG},
            asm.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Metric(
                    "fs_used",
                    316283.0,
                    levels=(2097152.0, 2359296.0),
                    boundaries=(0.0, 2621440.0),
                ),
                Metric(
                    "fs_size",
                    2621440.0,
                    boundaries=(0.0, None),
                ),
                Metric(
                    "fs_used_percent",
                    12.065238952636719,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=state.OK, summary="12.07% used (309 GiB of 2.50 TiB)"),
                Metric("growth", -4423.433540694911),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -4.32 GiB"),
                Result(state=state.OK, summary="trend per 1 day 0 hours: -0.17%"),
                Metric(
                    "trend",
                    -4423.433540694911,
                    levels=(None, None),
                    boundaries=(0.0, 109226.66666666667),
                ),
                Result(
                    state=state.OK,
                    summary="normal redundancy, old plugin data, possible wrong used and free space",
                ),
            ],
        ),
    ],
)
def test_cluster(value_store_patch, section, params, expected) -> None:
    with on_time(*NOW_SIMULATED):
        yielded_results = list(asm.cluster_check_oracle_asm_diskgroup(ITEM, params, section))
        assert yielded_results == expected
