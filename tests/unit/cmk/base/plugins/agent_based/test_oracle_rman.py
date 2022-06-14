#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import oracle_rman
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


def get_parsed_section() -> oracle_rman.SectionOracleRman:
    return {
        "AFIS11.ARCHIVELOG": {
            "backupage": 103,
            "backuplevel": "",
            "backupscn": -1,
            "backuptype": "ARCHIVELOG",
            "sid": "AFIS11",
            "status": "COMPLETED",
            "used_incr_0": False,
        },
        "AFIS2.DB_INCR_0": {
            "backupage": 460,
            "backuplevel": "0",
            "backupscn": 545791334,
            "backuptype": "DB_INCR",
            "sid": "AFIS2",
            "status": "COMPLETED",
            "used_incr_0": False,
        },
        "TUX2.DB_INCR": {
            "backupage": 32,
            "backuplevel": "-1",
            "backupscn": -1,
            "backuptype": "DB_INCR",
            "sid": "TUX2",
            "status": "COMPLETED",
            "used_incr_0": False,
        },
    }


@pytest.mark.parametrize(
    "string_table, parsed",
    [
        pytest.param(
            [
                [
                    "AFIS2",
                    "COMPLETED",
                    "2016-07-12_02:05:39",
                    "2016-07-12_02:05:39",
                    "DB_INCR",
                    "0",
                    "460",
                    "545791334",
                ],
                [
                    "AFIS11",
                    "COMPLETED",
                    "2016-07-12_09:50:46",
                    "2016-07-12_08:08:05",
                    "ARCHIVELOG",
                    "",
                    "103",
                    "",
                ],
                [
                    "TUX2",
                    "COMPLETED",
                    "2014-07-08_17:27:59",
                    "2014-07-08_17:29:35",
                    "DB_INCR",
                    "32",
                ],
            ],
            get_parsed_section(),
            id="normal case",
        ),
        pytest.param(
            [
                [
                    "AFIS2",
                    "COMPLETED",
                    "2016-07-12_02:05:39",
                    "2016-07-12_02:05:39",
                    "DB_INCR",
                    "0",
                    "-5",
                    "545791334",
                ],
            ],
            {
                "AFIS2.DB_INCR_0": {
                    "backupage": 0,
                    "backuplevel": "0",
                    "backupscn": 545791334,
                    "backuptype": "DB_INCR",
                    "sid": "AFIS2",
                    "status": "COMPLETED",
                    "used_incr_0": False,
                },
            },
            id="backupage < 0",
        ),
    ],
)
def test_parse(
    string_table: StringTable,
    parsed: oracle_rman.SectionOracleRman,
) -> None:
    assert oracle_rman.parse_oracle_rman(string_table) == parsed


def test_discovery() -> None:
    yielded_services = list(oracle_rman.discovery_oracle_rman(get_parsed_section()))
    assert yielded_services == [
        Service(item="AFIS11.ARCHIVELOG", parameters={}, labels=[]),
        Service(item="AFIS2.DB_INCR_0", parameters={}, labels=[]),
        Service(item="TUX2.DB_INCR_-1", parameters={}, labels=[]),
    ]


@pytest.mark.parametrize(
    "item, params, section, results",
    [
        (
            "AFIS11.ARCHIVELOG",
            {"levels": (50, 60)},
            get_parsed_section(),
            [
                Result(
                    state=state.CRIT,
                    summary="Time since last backup: 1 hour 43 minutes (warn/crit at 50 seconds/1 minute 0 seconds)",
                    details="Time since last backup: 1 hour 43 minutes (warn/crit at 50 seconds/1 minute 0 seconds)",
                ),
                Metric("age", 6180.0, levels=(50.0, 60.0)),
            ],
        ),
        (
            "AFIS11.ARCHIVELOG",
            {},
            get_parsed_section(),
            [
                Result(
                    state=state.OK,
                    summary="Time since last backup: 1 hour 43 minutes",
                    details="Time since last backup: 1 hour 43 minutes",
                ),
                Metric("age", 6180.0),
            ],
        ),
        (
            "AFIS2.DB_INCR_1",
            {},
            get_parsed_section(),
            [
                Result(
                    state=state.OK,
                    summary="Time since last backup: 7 hours 40 minutes",
                    details="Time since last backup: 7 hours 40 minutes",
                ),
                Metric("age", 27600.0),
                Result(
                    state=state.OK,
                    summary="Incremental SCN 545791334",
                    details="Incremental SCN 545791334",
                ),
                Result(state=state.OK, summary="Last DB_INCR_0 used"),
            ],
        ),
    ],
)
def test_check(item, params, section, results) -> None:
    yielded_results = list(oracle_rman.check_oracle_rman(item, params, section))
    assert yielded_results == results


def test_check_raises() -> None:
    with pytest.raises(IgnoreResultsError) as exc:
        list(oracle_rman.check_oracle_rman("NON-EXISTANT-ITEM", {}, get_parsed_section()))
    assert "Login into database failed. Working on NON-EXISTANT-ITEM" in str(exc.value)


def test_cluster_check() -> None:
    item = "TUX2.DB_INCR"
    parsed_section_2 = get_parsed_section()
    parsed_section_2[item]["backupage"] = 1
    parsed_section_3 = get_parsed_section()
    parsed_section_3[item]["backupage"] = None
    node_sections = {
        "node1": get_parsed_section(),
        "node2": parsed_section_2,
        "node3": parsed_section_3,
    }
    yielded_results = list(oracle_rman.cluster_check_oracle_rman(item, {}, node_sections))
    assert [
        Result(
            state=state.OK,
            summary="Time since last backup: 1 minute 0 seconds",
            details="Time since last backup: 1 minute 0 seconds",
        ),
        Metric("age", 60.0),
    ] == yielded_results


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                [
                    "MYDB",
                    "COMPLETED",
                    "2021-11-15_23:46:05",
                    "2021-11-15_23:46:05",
                    "DB_INCR",
                    "1",
                    "15045",
                    "1014721683",
                ],
                [
                    "MYDB",
                    "COMPLETED",
                    "2021-11-26_10:19:28",
                    "2021-11-26_10:19:28",
                    "DB_INCR",
                    "1",
                    "12",
                    "1022591235",
                ],
            ],
            {
                "MYDB.DB_INCR_1": {
                    "sid": "MYDB",
                    "backuptype": "DB_INCR",
                    "backuplevel": "1",
                    "backupage": 12,
                    "status": "COMPLETED",
                    "backupscn": 1022591235,
                    "used_incr_0": False,
                },
            },
            id="Latest backup is written to section in case of multiple backups for the same item",
        ),
    ],
)
def test_parse_oracle_rman(string_table, section) -> None:
    assert oracle_rman.parse_oracle_rman(string_table) == section
