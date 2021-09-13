#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Note: this test only tests `parse_f5_bigip_vcmpfailover()` since f5_bigip_vcmpfailover
#       uses function from f5_bigip_cluster_status

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.printer_pages import parse_printer_pages
from cmk.base.plugins.agent_based.printer_pages_canon import parse_printer_pages_canon
from cmk.base.plugins.agent_based.printer_pages_ricoh import parse_printer_pages_ricoh
from cmk.base.plugins.agent_based.utils.printer import check_printer_pages_types


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[]], None),
        ([[["585"]]], {"pages_total": 585}),
    ],
)
def test_parse_printer_pages(string_table, expected_parsed_data):
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
def test_parse_printer_pages_canon(string_table, expected_parsed_data):
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
def test_parse_printer_pages_ricoh(string_table, expected_parsed_data):
    assert parse_printer_pages_ricoh(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,expected_results",
    [
        (
            {"pages_color": 21693, "pages_bw": 54198},
            [
                Result(state=state.OK, summary="total prints: 75891"),
                Metric("pages_total", 75891.0),
                Result(state=state.OK, summary="b/w: 54198"),
                Metric("pages_bw", 54198.0),
                Result(state=state.OK, summary="color: 21693"),
                Metric("pages_color", 21693.0),
            ],
        ),
    ],
)
def test_check_printer_pages_types(section, expected_results):
    assert list(check_printer_pages_types(section)) == expected_results


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
