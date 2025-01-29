#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import sap_hana_status
from cmk.plugins.lib.sap_hana import ParsedSection

ITEM = "H90 33"
SECTION = {
    "Status %s" % ITEM: {"instance": ITEM, "message": "Yes", "state_name": "OK"},
    "Version %s" % ITEM: {"instance": ITEM, "version": "1.00.122.22.1543461992 (fa/hana1sp12)"},
}
SECTION_WARNING = {
    "Status %s" % ITEM: {"instance": ITEM, "message": "Yes", "state_name": "WARNING"},
    "Version %s" % ITEM: {"instance": ITEM, "version": "1.00.122.22.1543461992 (fa/hana1sp12)"},
}
SECTION_ERROR = {
    "Status %s" % ITEM: {
        "instance": ITEM,
        "message": "hdbsql ERROR: There was an error",
        "state_name": "error",
    },
}


@pytest.mark.parametrize(
    "string_table_row, expected_parsed_data",
    [
        (
            [
                ["[[H62 10]]"],
                ["Version", "", "1.00.122.22.1543461992 (fa/hana1sp12)"],
                ["All Started", "OK", "Yes"],
                ["[[H90 33]]"],
                ["Version", "", "1.00.122.22.1543461992 (fa/hana1sp12)"],
                ["All Started", "OK", "Yes"],
            ],
            {
                "Status H62 10": {"instance": "H62 10", "message": "Yes", "state_name": "OK"},
                "Version H62 10": {
                    "instance": "H62 10",
                    "version": "1.00.122.22.1543461992 (fa/hana1sp12)",
                },
                "Status H90 33": {"instance": "H90 33", "message": "Yes", "state_name": "OK"},
                "Version H90 33": {
                    "instance": "H90 33",
                    "version": "1.00.122.22.1543461992 (fa/hana1sp12)",
                },
            },
        ),
        (
            [
                ["[[H62 10]]"],
            ],
            {},
        ),
        (
            [
                ["[[H62 10]]"],
                ["hdbsql ERROR: There was an error"],
            ],
            {
                "Status H62 10": {
                    "instance": "H62 10",
                    "message": "hdbsql ERROR: There was an error",
                    "state_name": "error",
                },
            },
        ),
    ],
)
def test_sap_hana_status_parse(
    string_table_row: StringTable, expected_parsed_data: ParsedSection
) -> None:
    assert sap_hana_status.parse_sap_hana_status(string_table_row) == expected_parsed_data


def test_sap_hana_status_discovery() -> None:
    assert list(sap_hana_status.discovery_sap_hana_status(SECTION)) == [
        Service(item="Status %s" % ITEM),
        Service(item="Version %s" % ITEM),
    ]


@pytest.mark.parametrize(
    "section, check_type, results",
    [
        (SECTION, "Status", Result(state=State.OK, summary="Status: OK, Details: Yes")),
        (
            SECTION,
            "Version",
            Result(
                state=State.OK,
                summary="Version: 1.00.122.22.1543461992 (fa/hana1sp12)",
                details="Version: 1.00.122.22.1543461992 (fa/hana1sp12)",
            ),
        ),
        (
            SECTION_WARNING,
            "Status",
            Result(state=State.WARN, summary="Status: WARNING, Details: Yes"),
        ),
        (
            SECTION_ERROR,
            "Status",
            Result(
                state=State.CRIT, summary="Status: error, Details: hdbsql ERROR: There was an error"
            ),
        ),
    ],
)
def test_sap_hana_status_check(check_type: str, results: Result, section: ParsedSection) -> None:
    yielded_results = list(sap_hana_status.check_sap_hana_status(f"{check_type} {ITEM}", section))
    assert yielded_results == [results]


@pytest.mark.parametrize("section, item", [({"Status H62 10": {}}, "Status H62 10")])
def test_sap_hana_status_check_stale(section: ParsedSection, item: str) -> None:
    with pytest.raises(IgnoreResultsError):
        list(sap_hana_status.check_sap_hana_status(item, section))


def test_sap_hana_status_cluster_check() -> None:
    section = {"node 1": SECTION, "node 2": SECTION_WARNING}
    yielded_results = list(
        sap_hana_status.cluster_check_sap_hana_status("Status %s" % ITEM, section)
    )
    assert yielded_results == [
        Result(state=State.OK, summary="Nodes: node 1, node 2"),
        Result(state=State.OK, summary="Status: OK, Details: Yes"),
    ]
