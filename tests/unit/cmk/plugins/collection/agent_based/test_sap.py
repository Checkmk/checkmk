#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import sap

SECTION = [
    sap.Entry(
        sid="sap_XYZ",
        state=State.OK,
        path="Nagios/Allgemein/Intern/ResponseTime",
        reading=249.0,
        unit="msec",
        output="",
    ),
    sap.Entry(
        sid="sap_XYZ",
        state=State.CRIT,
        path="Nagios/Allgemein/Intern/ResponseTimeDialog",
        reading=249.0,
        unit="msec",
        output="",
    ),
]


@pytest.mark.parametrize(
    "string_table_row, expected_parsed_data",
    [
        (
            [
                ["sap_XYZ", "1", "50", "Nagios/Allgemein/Intern/ResponseTime", "249", "msec"],
                ["sap_XYZ", "2", "50", "Nagios/Allgemein/Intern/ResponseTimeDialog", "249", "msec"],
                [
                    "sap_XYZ",
                    "3",
                    "50",
                    "Nagios/Allgemein/Intern/ResponseTimeDialogRFC",
                    "249",
                    "msec",
                ],
                ["sap_XYZ", "1", "50", "Nagios/Allgemein/Intern/ResponseTimeHTTP", "9830", "msec"],
                [
                    "sap_XYZ",
                    "1",
                    "50",
                    "Nagios/Allgemein/Intern/FrontendResponseTime",
                    "542",
                    "msec",
                ],
            ],
            [
                sap.Entry(
                    sid="sap_XYZ",
                    state=State.OK,
                    path="Nagios/Allgemein/Intern/ResponseTime",
                    reading=249.0,
                    unit="msec",
                    output="",
                ),
                sap.Entry(
                    sid="sap_XYZ",
                    state=State.WARN,
                    path="Nagios/Allgemein/Intern/ResponseTimeDialog",
                    reading=249.0,
                    unit="msec",
                    output="",
                ),
                sap.Entry(
                    sid="sap_XYZ",
                    state=State.CRIT,
                    path="Nagios/Allgemein/Intern/ResponseTimeDialogRFC",
                    reading=249.0,
                    unit="msec",
                    output="",
                ),
                sap.Entry(
                    sid="sap_XYZ",
                    state=State.OK,
                    path="Nagios/Allgemein/Intern/ResponseTimeHTTP",
                    reading=9830.0,
                    unit="msec",
                    output="",
                ),
                sap.Entry(
                    sid="sap_XYZ",
                    state=State.OK,
                    path="Nagios/Allgemein/Intern/FrontendResponseTime",
                    reading=542.0,
                    unit="msec",
                    output="",
                ),
            ],
        ),
    ],
)
def test_sap_parse(string_table_row: StringTable, expected_parsed_data: sap.Section) -> None:
    assert sap.parse_sap(string_table_row) == expected_parsed_data


@pytest.mark.parametrize(
    "match, expected_services",
    (
        (
            ("all", ""),
            [
                Service(item="sap_XYZ Nagios/Allgemein/Intern/ResponseTime"),
                Service(item="sap_XYZ Nagios/Allgemein/Intern/ResponseTimeDialog"),
            ],
        ),
        (
            ("pattern", ".*ResponseTimeDialog$"),
            [Service(item="sap_XYZ Nagios/Allgemein/Intern/ResponseTimeDialog")],
        ),
        (("pattern", "$^"), []),
    ),
)
def test_sap_value_discovery(match: tuple[str, str], expected_services: list[Service]) -> None:
    assert list(sap.discover_sap_value([{"match": match}], SECTION)) == expected_services


@pytest.mark.parametrize(
    "item, params, results",
    [
        (
            "sap_XYZ Nagios/Allgemein/Intern/ResponseTime",
            {},
            [Metric("value", 249.0), Result(state=State.OK, summary="249.00msec")],
        ),
        (
            "sap_XYZ Nagios/Allgemein/Intern/ResponseTime",
            {"limit_item_levels": 5},
            [Metric("value", 249.0), Result(state=State.OK, summary="249.00msec")],
        ),
        (
            "sap_XYZ Nagios/Allgemein/Intern/ResponseTime",
            {"limit_item_levels": 1},
            None,
        ),
    ],
)
def test_sap_check(item: str, params: dict[str, int], results: CheckResult | None) -> None:
    if results is None:
        with pytest.raises(IgnoreResultsError):
            list(sap.check_sap_value(item, params, SECTION))
    else:
        assert list(sap.check_sap_value(item, params, SECTION)) == results
