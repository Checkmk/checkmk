#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.logwatch.agent_based import commons as logwatch
from cmk.plugins.logwatch.agent_based.logwatch_section import parse_logwatch

INFO = [
    ["[[[/tmp/my_test_log]]]"],
    ["BATCH:", "1656941120-74143101832552231232468562412716838190224"],
    ["W", "you", "have", "been", "warned"],
    ["[[[/tmp/my_test_log]]]"],
    ["BATCH:", "1656941057-446349206228817512034160204821044623126"],
    ["C", "this", "is", "critical"],
]


SECTION = logwatch.Section(
    errors=[],
    logfiles={
        "/tmp/my_test_log": {
            "attr": "ok",
            "lines": {
                "1656941120-74143101832552231232468562412716838190224": [
                    "W you have been warned",
                ],
                "1656941057-446349206228817512034160204821044623126": [
                    "C this is critical",
                ],
            },
        }
    },
)


def test_logwatch_ec_inventory_single() -> None:
    assert parse_logwatch(INFO) == SECTION


def test_logwatch_unseen_lines_new() -> None:
    assert logwatch.extract_unseen_lines(SECTION.logfiles["/tmp/my_test_log"]["lines"], ()) == [
        "C this is critical",
        "W you have been warned",
    ]


def test_logwatch_unseen_lines() -> None:
    assert logwatch.extract_unseen_lines(
        SECTION.logfiles["/tmp/my_test_log"]["lines"],
        {"1656941057-446349206228817512034160204821044623126"},
    ) == [
        "W you have been warned",
    ]
