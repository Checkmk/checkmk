#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timezone

import pytest  # type: ignore[import]
from freezegun import freeze_time  # type: ignore[import]

import cmk.base.plugins.agent_based.sap_hana_backup as sap_hana_backup
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

NOW_SIMULATED = "2019-01-01 22:00:00.000000"
ITEM = "inst"
SECTION: sap_hana_backup.Section = {
    ITEM: {
        'end_time': datetime(2019, 1, 1, 0, 0, tzinfo=timezone.utc),
        'state_name': 'successful',
        'comment': '',
        'message': '<ok>'
    }
}


@pytest.mark.parametrize("string_table_row, expected_parsed_data", [
    (
        [
            ["[[Crap its broken]]"],
            ["data snapshot", "?", "failed", "", ""],
            [
                "complete data backup",
                "2042-23-23 23:23:23.424242420",
                "failed",
                "",
                ("[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0."
                 " console output: No additional Information was received, [110203] Not all data could be"
                 " written: Expected 4096 but transferred 0"),
            ],
        ],
        {
            'Crap its broken - data snapshot': {
                "end_time": None,
                'state_name': 'failed',
                'comment': '',
                'message': ''
            },
            "Crap its broken - complete data backup": {
                'end_time': None,
                'state_name': 'failed',
                'comment': '',
                'message': '[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0. console output: No additional Information was received, [110203] Not all data could be written: Expected 4096 but transferred 0'
            }
        },
    ),
])
def test_parse(string_table_row, expected_parsed_data):
    assert sap_hana_backup.parse_sap_hana_backup(string_table_row) == expected_parsed_data


def test_discovery_sap_hana_backup():

    section: sap_hana_backup.Section = {
        "SAP INSTANCE - Backup": {},
        "SAP INSTANCE - Log": {},
    }
    assert list(sap_hana_backup.discovery_sap_hana_backup(section)) == [
        Service(item="SAP INSTANCE - Backup"),
        Service(item="SAP INSTANCE - Log")
    ]


@freeze_time(NOW_SIMULATED)
def test_check_sap_hana_backup_OK():

    params = {"backup_age": (24 * 60 * 60, 2 * 24 * 60 * 60)}
    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))

    assert yielded_results[0] == Result(state=State.OK, summary="Status: successful")

    rendered_timestamp = yielded_results[1]
    assert isinstance(rendered_timestamp, Result)
    assert rendered_timestamp.state == State.OK
    assert rendered_timestamp.summary.startswith("Last: Jan 01 2019")

    assert yielded_results[2:] == [
        Result(state=State.OK, summary="Age: 22 hours 0 minutes",
               details="Age: 22 hours 0 minutes"),
        Metric("backup_age", 79200.0, levels=(86400.0, 172800.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@freeze_time(NOW_SIMULATED)
def test_check_sap_hana_backup_CRIT():
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))

    assert yielded_results[0] == Result(state=State.OK, summary="Status: successful")

    rendered_timestamp = yielded_results[1]
    assert isinstance(rendered_timestamp, Result)
    assert rendered_timestamp.state == State.OK
    assert rendered_timestamp.summary.startswith("Last: Jan 01 2019")

    assert yielded_results[2:] == [
        Result(
            state=State.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@freeze_time(NOW_SIMULATED)
def test_cluster_check_sap_hana_backup_CRIT():
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    section = {"node0": SECTION, "node1": SECTION}

    yielded_results = list(sap_hana_backup.cluster_check_sap_hana_backup(ITEM, params, section))

    assert yielded_results[:2] == [
        Result(state=State.OK, summary="Nodes: node0, node1"),
        Result(state=State.OK, summary="Status: successful"),
    ]

    rendered_timestamp = yielded_results[2]
    assert isinstance(rendered_timestamp, Result)
    assert rendered_timestamp.state == State.OK
    assert rendered_timestamp.summary.startswith("Last: Jan 01 2019")

    assert yielded_results[3:] == [
        Result(
            state=State.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@freeze_time(NOW_SIMULATED)
def test_cluster_check_sap_hana_backup_missing_node_data():
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    section = {"node0": None, "node1": SECTION}

    assert list(sap_hana_backup.cluster_check_sap_hana_backup(ITEM, params, section))
