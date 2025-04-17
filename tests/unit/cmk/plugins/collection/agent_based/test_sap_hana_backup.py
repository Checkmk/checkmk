#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, UTC
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import sap_hana_backup

NOW_SIMULATED = datetime(2019, 1, 1, 22, tzinfo=ZoneInfo("UTC"))
ITEM = "inst"
SECTION = {
    ITEM: sap_hana_backup.Backup(
        end_time=datetime(2019, 1, 1, 0, 0, tzinfo=UTC),
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
                    end_time=None,
                    state_name="failed",
                    comment="",
                    message="",
                ),
                "Crap its broken - complete data backup": sap_hana_backup.Backup(
                    end_time=None,
                    state_name="failed",
                    comment="",
                    message="[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0. console output: No additional Information was received, [110203] Not all data could be written: Expected 4096 but transferred 0",
                ),
            },
        )
    ],
)
def test_parse(
    string_table_row: StringTable, expected_parsed_data: sap_hana_backup.Section
) -> None:
    assert sap_hana_backup.parse_sap_hana_backup(string_table_row) == expected_parsed_data


def test_discovery_sap_hana_backup() -> None:
    section = {
        "SAP INSTANCE - Backup": sap_hana_backup.Backup(),
        "SAP INSTANCE - Log": sap_hana_backup.Backup(),
    }
    assert list(sap_hana_backup.discovery_sap_hana_backup(section)) == [
        Service(item="SAP INSTANCE - Backup"),
        Service(item="SAP INSTANCE - Log"),
    ]


@time_machine.travel(NOW_SIMULATED)
def test_check_sap_hana_backup_OK() -> None:
    params = {"backup_age": (24 * 60 * 60, 2 * 24 * 60 * 60)}
    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))

    assert yielded_results[0] == Result(state=State.OK, summary="Status: successful")

    rendered_timestamp = yielded_results[1]
    assert isinstance(rendered_timestamp, Result)
    assert rendered_timestamp.state == State.OK
    assert rendered_timestamp.summary.startswith("Last: 2019-01-01")

    assert yielded_results[2:] == [
        Result(
            state=State.OK, summary="Age: 22 hours 0 minutes", details="Age: 22 hours 0 minutes"
        ),
        Metric("backup_age", 79200.0, levels=(86400.0, 172800.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@time_machine.travel(NOW_SIMULATED)
def test_check_sap_hana_backup_CRIT() -> None:
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}
    yielded_results = list(sap_hana_backup.check_sap_hana_backup(ITEM, params, SECTION))

    assert yielded_results[0] == Result(state=State.OK, summary="Status: successful")

    rendered_timestamp = yielded_results[1]
    assert isinstance(rendered_timestamp, Result)
    assert rendered_timestamp.state == State.OK
    assert rendered_timestamp.summary.startswith("Last: 2019-01-01")

    assert yielded_results[2:] == [
        Result(
            state=State.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@time_machine.travel(NOW_SIMULATED)
def test_cluster_check_sap_hana_backup_CRIT() -> None:
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
    assert rendered_timestamp.summary.startswith("Last: 2019-01-01")

    assert yielded_results[3:] == [
        Result(
            state=State.CRIT,
            summary="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
            details="Age: 22 hours 0 minutes (warn/crit at 1 hour 0 minutes/2 hours 0 minutes)",
        ),
        Metric("backup_age", 79200.0, levels=(3600.0, 7200.0)),
        Result(state=State.OK, summary="Message: <ok>"),
    ]


@time_machine.travel(NOW_SIMULATED)
def test_cluster_check_sap_hana_backup_missing_node_data() -> None:
    params = {"backup_age": (1 * 60 * 60, 2 * 60 * 60)}

    section = {"node0": None, "node1": SECTION}

    assert list(sap_hana_backup.cluster_check_sap_hana_backup(ITEM, params, section))


def test_check_sap_hana_backup_empty() -> None:
    section_with_empty_backup = {ITEM: sap_hana_backup.Backup()}
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_backup.check_sap_hana_backup(ITEM, {}, section_with_empty_backup))


def test_cluster_check_sap_hana_backup_empty() -> None:
    section_with_empty_backup = {ITEM: sap_hana_backup.Backup()}
    section_by_node = {"node0": section_with_empty_backup}
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_backup.cluster_check_sap_hana_backup(ITEM, {}, section_by_node))


def test_cluster_check_sap_hana_backup_unexisting_item() -> None:
    section_by_node = {"node0": SECTION}
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_backup.cluster_check_sap_hana_backup("unexisting_item", {}, section_by_node))
