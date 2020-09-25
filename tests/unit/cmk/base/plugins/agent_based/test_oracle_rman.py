#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    IgnoreResultsError,
    Metric,
    Result,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based import oracle_rman

PARSED_SECTION: oracle_rman.SectionOracleRman = {
    'AFIS11.ARCHIVELOG': {
        'backupage': 103,
        'backuplevel': '',
        'backupscn': -1,
        'backuptype': 'ARCHIVELOG',
        'sid': 'AFIS11',
        'status': 'COMPLETED',
        'used_incr_0': False
    },
    'AFIS2.DB_INCR_0': {
        'backupage': 460,
        'backuplevel': '0',
        'backupscn': 545791334,
        'backuptype': 'DB_INCR',
        'sid': 'AFIS2',
        'status': 'COMPLETED',
        'used_incr_0': False
    },
    'TUX2.DB_INCR': {
        'backupage': 32,
        'backuplevel': "-1",
        'backupscn': -1,
        'backuptype': 'DB_INCR',
        'sid': 'TUX2',
        'status': 'COMPLETED',
        'used_incr_0': False
    },
}


@pytest.mark.parametrize("string_table, parsed", [([
    [
        'AFIS2', 'COMPLETED', '2016-07-12_02:05:39', '2016-07-12_02:05:39', 'DB_INCR', '0', '460',
        '545791334'
    ],
    [
        'AFIS11', 'COMPLETED', '2016-07-12_09:50:46', '2016-07-12_08:08:05', 'ARCHIVELOG', '',
        '103', ''
    ],
    ["TUX2", "COMPLETED", "2014-07-08_17:27:59", "2014-07-08_17:29:35", "DB_INCR", "32"],
], PARSED_SECTION)])
def test_parse(string_table, parsed):
    assert oracle_rman.parse_oracle_rman(string_table) == parsed


def test_discovery():
    yielded_services = list(oracle_rman.discovery_oracle_rman(PARSED_SECTION))
    assert yielded_services == [
        Service(item="AFIS11.ARCHIVELOG", parameters={}, labels=[]),
        Service(item="AFIS2.DB_INCR_0", parameters={}, labels=[]),
        Service(item='TUX2.DB_INCR_-1', parameters={}, labels=[])
    ]


@pytest.mark.parametrize("item, params, section, results", [
    (
        "AFIS11.ARCHIVELOG",
        {
            "levels": (50, 60)
        },
        PARSED_SECTION,
        [
            Result(
                state=state.CRIT,
                summary=
                'Time since last backup: 1 hour 43 minutes (warn/crit at 50 seconds/1 minute 0 seconds)',
                details=
                'Time since last backup: 1 hour 43 minutes (warn/crit at 50 seconds/1 minute 0 seconds)'
            ),
            Metric('age', 6180.0, levels=(50.0, 60.0), boundaries=(None, None)),
        ],
    ),
    (
        "AFIS11.ARCHIVELOG",
        {},
        PARSED_SECTION,
        [
            Result(state=state.OK,
                   summary='Time since last backup: 1 hour 43 minutes',
                   details='Time since last backup: 1 hour 43 minutes'),
            Metric('age', 6180.0, levels=(None, None), boundaries=(None, None)),
        ],
    ),
    (
        "AFIS2.DB_INCR_1",
        {},
        PARSED_SECTION,
        [
            Result(state=state.OK,
                   summary='Time since last backup: 7 hours 40 minutes',
                   details='Time since last backup: 7 hours 40 minutes'),
            Metric('age', 27600.0, levels=(None, None), boundaries=(None, None)),
            Result(state=state.OK,
                   summary='Incremental SCN 545791334',
                   details='Incremental SCN 545791334'),
            Result(state=state.OK, summary='Last DB_INCR_0 used', details='Last DB_INCR_0 used'),
        ],
    ),
])
def test_check(item, params, section, results):
    yielded_results = list(oracle_rman.check_oracle_rman(item, params, section))
    assert yielded_results == results


def test_check_raises():
    with pytest.raises(IgnoreResultsError) as exc:
        list(
            oracle_rman.check_oracle_rman("NON-EXISTANT-ITEM", type_defs.Parameters({}),
                                          PARSED_SECTION))
    assert "Login into database failed. Working on NON-EXISTANT-ITEM" in str(exc.value)


def test_cluster_check():
    item = 'TUX2.DB_INCR'
    PARSED_SECTION2 = copy.deepcopy(PARSED_SECTION)
    PARSED_SECTION2[item]['backupage'] = 1
    PARSED_SECTION3 = copy.deepcopy(PARSED_SECTION)
    PARSED_SECTION3[item]['backupage'] = None
    node_sections = {"node1": PARSED_SECTION, "node2": PARSED_SECTION2, "node3": PARSED_SECTION3}
    yielded_results = list(
        oracle_rman.cluster_check_oracle_rman(item, type_defs.Parameters({}), node_sections))
    assert [
        Result(state=state.OK,
               summary='Time since last backup: 1 minute 0 seconds',
               details='Time since last backup: 1 minute 0 seconds'),
        Metric('age', 60.0, levels=(None, None), boundaries=(None, None))
    ] == yielded_results
