#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from freezegun import freeze_time

import cmk.base.plugins.agent_based.sap_hana_backup as sap_hana_backup
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

NOW_SIMULATED = "2019-01-01 22:00:00.000000"
ITEM = "inst"
SECTION = {
    ITEM: sap_hana_backup.Backup(
        sys_end_time=1546300800,
        backup_time_readable="2019-01-01 00:00:00",
        state_name="successful",
        comment="",
        message="<ok>",
    )
}


@pytest.mark.parametrize(
    "string_table_row, expected_parsed_data",
    [
        (
            [
                ["[[Crap its broken]]"],
                ["data snapshot", "?", "failed", "", ""],
                [
                    "complete data backup",
                    "2042-23-23 23:23:23.424242420",
                    "failed",
                    "",
                    (
                        "[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0."
                        " console output: No additional Information was received, [110203] Not all data could be"
                        " written: Expected 4096 but transferred 0"
                    ),
                ],
            ],
            {
                "Crap its broken - data snapshot": sap_hana_backup.Backup(
                    sys_end_time=None,
                    backup_time_readable="?",
                    state_name="failed",
                    comment="",
                    message="",
                ),
                "Crap its broken - complete data backup": sap_hana_backup.Backup(
                    sys_end_time=None,
                    backup_time_readable="2042-23-23 23:23:23",
                    state_name="failed",
                    comment="",
                    message="[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0. console output: No additional Information was received, [110203] Not all data could be written: Expected 4096 but transferred 0",
                ),
            },
        )
    ],
)
def test_parse(string_table_row, expected_parsed_data):
    assert sap_hana_backup.parse_sap_hana_backup(string_table_row) == expected_parsed_data


def test_discovery_sap_hana_backup():

    section = {"SAP INSTANCE - Backup": "some data", "SAP INSTANCE - Log": "some other data"}
    assert list(sap_hana_backup.discovery_sap_hana_backup(section)) == [
        Service(item="SAP INSTANCE - Backup"),
        Service(item="SAP INSTANCE - Log"),
    ]


@freeze_time(NOW_SIMULATED)
def test_check_sap_hana_backup_OK():

    params = {"backup_age": (24 * 60 * 60, 2 * 24 * 60 * 60)}
    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))
    assert yielded_results == [
        Result(state=state.OK, summary="Status: successful"),
        Result(
            state=state.OK, summary="Last: 2019-01-01 00:00:00", details="Last: 2019-01-01 00:00:00"
        ),
        Result(
            state=state.OK, summary="Age: 22 hours 0 minutes", details="Age: 22 hours 0 minutes"
        ),
        Metric("backup_age", 79200.0, levels=(86400.0, 172800.0)),
        Result(state=state.OK, summary="Message: <ok>"),
    ]


@freeze_time(NOW_SIMULATED)
def test_check_sap_hana_backup_CRIT():
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))

    assert yielded_results == [
        Result(state=state.OK, summary="Status: successful"),
        Result(
            state=state.OK, summary="Last: 2019-01-01 00:00:00", details="Last: 2019-01-01 00:00:00"
        ),
        Result(
            state=state.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=state.OK, summary="Message: <ok>"),
    ]


@freeze_time(NOW_SIMULATED)
def test_cluster_check_sap_hana_backup_CRIT():
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    section = {"node0": SECTION, "node1": SECTION}

    yielded_results = list(sap_hana_backup.cluster_check_sap_hana_backup(ITEM, params, section))

    assert yielded_results == [
        Result(state=state.OK, summary="Nodes: node0, node1"),
        Result(state=state.OK, summary="Status: successful"),
        Result(
            state=state.OK, summary="Last: 2019-01-01 00:00:00", details="Last: 2019-01-01 00:00:00"
        ),
        Result(
            state=state.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=state.OK, summary="Message: <ok>"),
    ]
