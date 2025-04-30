#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Note: this test only tests `parse_f5_bigip_vcmpfailover()` since f5_bigip_vcmpfailover
#       uses function from f5_bigip_cluster_status

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.printer_pages import parse_printer_pages
from cmk.plugins.collection.agent_based.printer_pages_canon import parse_printer_pages_canon
from cmk.plugins.collection.agent_based.printer_pages_ricoh import parse_printer_pages_ricoh
from cmk.plugins.lib.printer import check_printer_pages_types, Section


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[]], None),
        ([[["585"]]], {"pages_total": 585}),
    ],
)
def test_parse_printer_pages(
    string_table: Sequence[StringTable], expected_parsed_data: Section | None
) -> None:
    assert parse_printer_pages(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[]], None),
        (
            [[["2240", "113"], ["1343", "123"], ["3464", "301"], ["122", "501"]]],
            {"pages_color_a3": 501},
        ),
    ],
)
def test_parse_printer_pages_canon(
    string_table: Sequence[StringTable], expected_parsed_data: Section | None
) -> None:
    assert parse_printer_pages_canon(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[]], None),
        (
            [
                [
                    ["Counter: Machine Total", "118722"],
                    ["Counter:Print:Total", "118722"],
                    ["Counter:Print:Black & White", "62846"],
                    ["Counter:Print:Full Color", "55876"],
                    ["Counter: Machine Total", "118722"],
                    ["Total Prints: Full Color", "55876"],
                    ["Total Prints: Monocolor", "62846"],
                    ["Development: Color", "167628"],
                    ["Development: Black & White", "118722"],
                    ["Printer: Color", "55876"],
                    ["Printer: Black & White", "62846"],
                    ["Total Prints: Color", "55876"],
                    ["Total Prints: Black & White", "62846"],
                    ["Printer: Black & White", "62846"],
                    ["Printer: Full Color", "55876"],
                ]
            ],
            {"pages_total": 118722, "pages_color": 55876, "pages_bw": 62846},
        ),
    ],
)
def test_parse_printer_pages_ricoh(
    string_table: Sequence[StringTable], expected_parsed_data: Section | None
) -> None:
    assert parse_printer_pages_ricoh(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,expected_results",
    [
        (
            {"pages_color": 21693, "pages_bw": 54198},
            [
                Result(state=State.OK, summary="total prints: 75891"),
                Metric("pages_total", 75891.0),
                Result(state=State.OK, summary="b/w: 54198"),
                Metric("pages_bw", 54198.0),
                Result(state=State.OK, summary="color: 21693"),
                Metric("pages_color", 21693.0),
            ],
        ),
    ],
)
def test_check_printer_pages_types(section: Section, expected_results: CheckResult) -> None:
    assert list(check_printer_pages_types(section)) == expected_results


_ = __name__ == "__main__" and pytest.main(["-svv", __file__])
