#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import on_time
from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based import value_store
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    State as state,
    Result,
    Metric,
    IgnoreResults,
)
import cmk.base.plugins.agent_based.oracle_asm_diskgroup as oracle_asm_diskgroup
NOW_SIMULATED = 581792400, "UTC"

ITEM = "DISK_GROUP"
SECTION_OLD_MOUNTED = {
    ITEM: {
        'dgstate': 'MOUNTED',
        'dgtype': 'NORMAL',
        'free_mb': '4610314',
        'offline_disks': '0',
        'req_mir_free_mb': '63320',
        'total_mb': '5242880',
        'voting_files': 'N'
    }
}
SECTION_UNKNOWN_ITEM = {"UNKNOWN": SECTION_OLD_MOUNTED[ITEM]}

SECTION_OLD_DISMOUNTED = {
    ITEM: {
        'dgstate': 'DISMOUNTED',
        'dgtype': None,
        'free_mb': '0',
        'offline_disks': '0',
        'req_mir_free_mb': '0',
        'total_mb': '0',
        'voting_files': 'N'
    }
}

SECTION_WITH_FG = {
    ITEM: {
        'dgstate': 'MOUNTED',
        'dgtype': 'EXTERN',
        'failgroups': [{
            'fg_disks': 1,
            'fg_free_mb': 489148,
            'fg_min_repair_time': 8640000,
            'fg_name': 'DATA_0000',
            'fg_total_mb': 614400,
            'fg_type': 'REGULAR',
            'fg_voting_files': 'N'
        }],
        'free_mb': '489148',
        'offline_disks': '0',
        'req_mir_free_mb': '0',
        'total_mb': '614400',
        'voting_files': 'N'
    }
}


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch):
    value_store_patched = {
        "oracle_asm_diskgroup.%s.delta" % ITEM: [2000000, 30000000],
    }
    monkeypatch.setattr(oracle_asm_diskgroup, 'get_value_store', lambda: value_store_patched)
    yield value_store_patched


@pytest.mark.parametrize(
    "string_table, expected",
    [([[]], {}),
     ([[
         'UNKNOWN-STATE', 'NORMAL', 'N', '512', '4096', '1048576', '5242880', '4610314', '63320',
         '2273497', '0', 'N',
         '%s/' % ITEM
     ]], {}),
     ([[
         'MOUNTED', 'NORMAL', 'N', '512', '4096', '1048576', '5242880', '4610314', '63320',
         '2273497', '0', 'N',
         '%s/' % ITEM
     ]], SECTION_OLD_MOUNTED),
     ([['DISMOUNTED', 'N', '0', '4096', '0', '0', '0', '0', '0', '0', 'N',
        '%s/' % ITEM]], SECTION_OLD_DISMOUNTED),
     ([[
         'MOUNTED', 'EXTERN',
         '%s/' % ITEM, '4096', '4194304', '0', '614400', '489148', 'DATA_0000', 'N', 'REGULAR', '0',
         '8640000', '1'
     ]], SECTION_WITH_FG)])
def test_parse(string_table, expected):
    parsed_section = oracle_asm_diskgroup.parse_oracle_asm_diskgroup(string_table)
    assert parsed_section == expected


@pytest.mark.parametrize("section, expected", [
    ({}, []),
    ({
        ITEM: {
            'dgstate': 'UNKNOW-DG-STATE'
        }
    }, []),
    ({
        ITEM: {
            'dgstate': 'MOUNTED'
        }
    }, [Service(item=ITEM)]),
    ({
        ITEM: {
            'dgstate': 'DISMOUNTED'
        }
    }, [Service(item=ITEM)]),
])
def test_discovery(section, expected):
    yielded_services = list(oracle_asm_diskgroup.discovery_oracle_asm_diskgroup(section))
    assert yielded_services == expected


@pytest.mark.parametrize(
    "section, params, expected",
    [
        (
            SECTION_UNKNOWN_ITEM,
            oracle_asm_diskgroup.ASM_DISKGROUP_DEFAULT_LEVELS,
            [(IgnoreResults('Diskgroup %s not found' % ITEM))],
        ),
        (
            SECTION_OLD_DISMOUNTED,
            oracle_asm_diskgroup.ASM_DISKGROUP_DEFAULT_LEVELS,
            [Result(state=state.CRIT, summary="Diskgroup dismounted")],
        ),
        (
            SECTION_OLD_MOUNTED,
            oracle_asm_diskgroup.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Metric(
                    'fs_used', 316283.0, levels=(2097152.0, 2359296.0),
                    boundaries=(0.0, 2621440.0)),
                Metric('fs_size', 2621440.0, levels=(None, None), boundaries=(None, None)),
                Metric('fs_used_percent',
                       12.065238952636719,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='12.1% used (309  of 2.50 TiB)',
                       details='12.1% used (309  of 2.50 TiB)'),
                Metric('growth', -4423.433540694911, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -4.32 GiB',
                       details='trend per 1 day 0 hours: -4.32 GiB'),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -0.17%',
                       details='trend per 1 day 0 hours: -0.17%'),
                Metric('trend',
                       -4423.433540694911,
                       levels=(None, None),
                       boundaries=(0.0, 109226.66666666667)),
                Result(
                    state=state.OK,
                    summary='normal redundancy, old plugin data, possible wrong used and free space',
                    details='normal redundancy, old plugin data, possible wrong used and free space'
                ),
            ],
        ),
        (
            SECTION_WITH_FG,
            oracle_asm_diskgroup.ASM_DISKGROUP_DEFAULT_LEVELS,
            [
                Metric('fs_used', 125252.0, levels=(491520.0, 552960.0),
                       boundaries=(0.0, 614400.0)),
                Metric('fs_size', 614400.0, levels=(None, None), boundaries=(None, None)),
                Metric('fs_used_percent',
                       20.386067708333332,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='20.4% used (122  of 600 GiB)',
                       details='20.4% used (122  of 600 GiB)'),
                Metric('growth', -4451.90076172092, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -4.35 GiB',
                       details='trend per 1 day 0 hours: -4.35 GiB'),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -0.72%',
                       details='trend per 1 day 0 hours: -0.72%'),
                Metric('trend', -4451.90076172092, levels=(None, None), boundaries=(0.0, 25600.0)),
                Result(state=state.OK,
                       summary='extern redundancy, 1 disks',
                       details='extern redundancy, 1 disks'),
            ],
        ),
        (
            SECTION_WITH_FG,
            {
                "req_mir_free": True,  # Ignore Requirre mirror free space in DG
            },
            [
                Metric('fs_used', 125252.0, levels=(491520.0, 552960.0),
                       boundaries=(0.0, 614400.0)),
                Metric('fs_size', 614400.0, levels=(None, None), boundaries=(None, None)),
                Metric('fs_used_percent',
                       20.386067708333332,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='20.4% used (122  of 600 GiB)',
                       details='20.4% used (122  of 600 GiB)'),
                Metric('growth', -4451.90076172092, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -4.35 GiB',
                       details='trend per 1 day 0 hours: -4.35 GiB'),
                Result(state=state.OK,
                       summary='trend per 1 day 0 hours: -0.72%',
                       details='trend per 1 day 0 hours: -0.72%'),
                Metric('trend', -4451.90076172092, levels=(None, None), boundaries=(0.0, 25600.0)),
                Result(state=state.OK,
                       summary='extern redundancy, 1 disks, required mirror free space used',
                       details='extern redundancy, 1 disks, required mirror free space used'),
            ],
        ),
    ])
def test_check(value_store_patch, section, params, expected):
    with on_time(*NOW_SIMULATED):
        with value_store.context(CheckPluginName("oracle_asm_diskgroup"), None):
            yielded_results = list(
                oracle_asm_diskgroup.check_oracle_asm_diskgroup(ITEM, params, section))
            assert yielded_results == expected


@pytest.mark.parametrize("section, params, expected", [
    (
        {
            "node1": SECTION_OLD_MOUNTED,
            "node2": SECTION_WITH_FG
        },
        oracle_asm_diskgroup.ASM_DISKGROUP_DEFAULT_LEVELS,
        [
            Metric('fs_used', 316283.0, levels=(2097152.0, 2359296.0), boundaries=(0.0, 2621440.0)),
            Metric('fs_size', 2621440.0, levels=(None, None), boundaries=(None, None)),
            Metric(
                'fs_used_percent', 12.065238952636719, levels=(None, None),
                boundaries=(None, None)),
            Result(state=state.OK,
                   summary='12.1% used (309  of 2.50 TiB)',
                   details='12.1% used (309  of 2.50 TiB)'),
            Metric('growth', -4423.433540694911, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK,
                   summary='trend per 1 day 0 hours: -4.32 GiB',
                   details='trend per 1 day 0 hours: -4.32 GiB'),
            Result(state=state.OK,
                   summary='trend per 1 day 0 hours: -0.17%',
                   details='trend per 1 day 0 hours: -0.17%'),
            Metric('trend',
                   -4423.433540694911,
                   levels=(None, None),
                   boundaries=(0.0, 109226.66666666667)),
            Result(
                state=state.OK,
                summary='normal redundancy, old plugin data, possible wrong used and free space',
                details='normal redundancy, old plugin data, possible wrong used and free space'),
        ],
    ),
])
def test_cluster(value_store_patch, section, params, expected):
    with on_time(*NOW_SIMULATED):
        with value_store.context(CheckPluginName("oracle_asm_diskgroup"), None):
            yielded_results = list(
                oracle_asm_diskgroup.cluster_check_oracle_asm_diskgroup(ITEM, params, section))
            assert yielded_results == expected
