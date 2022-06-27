#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check


@pytest.mark.parametrize(
    "parsed, expected",
    [
        (
            {
                "Pumpe 0": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
                "Pumpe 1": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
                "Pumpe 2": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
            },
            [("Pumpe 0", {}), ("Pumpe 1", {}), ("Pumpe 2", {})],
        )
    ],
)
def test_apc_netbotz_drycontact_inventory(parsed, expected) -> None:

    check = Check("apc_netbotz_drycontact")
    assert list(check.run_discovery(parsed)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [
                ["1.6", "Pumpe 0 RZ4", "Kaeltepark RZ4", "2"],
                ["2.5", "Pumpe 1 RZ4", "Kaeltepark RZ4", "1"],
                ["2.6", "Pumpe 2 RZ4", "Kaeltepark RZ4", "3"],
            ],
            {
                "Pumpe 0 RZ4 1.6": {"location": "Kaeltepark RZ4", "state": ("Open low mem", 0)},
                "Pumpe 1 RZ4 2.5": {"location": "Kaeltepark RZ4", "state": ("Closed high mem", 2)},
                "Pumpe 2 RZ4 2.6": {"location": "Kaeltepark RZ4", "state": ("Disabled", 1)},
            },
        ),
        (
            [["1.6", "Leckagekontrolle-RZ4", "Kaeltepark RZ4", "25"]],
            {
                "Leckagekontrolle-RZ4 1.6": {
                    "location": "Kaeltepark RZ4",
                    "state": ("unknown[25]", 3),
                }
            },
        ),
        (
            [["1.6", "Pumpe 1", "Kaeltepark RZ4", "3"]],
            {"Pumpe 1 1.6": {"location": "Kaeltepark RZ4", "state": ("Disabled", 1)}},
        ),
        ([], {}),
    ],
)
def test_apc_netbotz_drycontact_parse(info, expected) -> None:

    check = Check("apc_netbotz_drycontact")
    assert check.run_parse(info) == expected


@pytest.mark.parametrize(
    "item, params, data, expected",
    [
        (
            "Pumpe 1",
            {},
            {"Pumpe 1": {"location": "Kaeltepark", "state": ("Open low mem", 0)}},
            (0, "[Kaeltepark] State: Open low mem"),
        ),
        (
            "Pumpe 2",
            {},
            {"Pumpe 2": {"location": "Waermepark", "state": ("Closed high mem", 2)}},
            (2, "[Waermepark] State: Closed high mem"),
        ),
        (
            "Pumpe 3",
            {},
            {"Pumpe 3": {"location": "Kaeltepark", "state": ("Disabled", 1)}},
            (1, "[Kaeltepark] State: Disabled"),
        ),
        (
            "Pumpe 4",
            {},
            {"Pumpe 4": {"location": "Kaeltepark", "state": ("Not applicable", 3)}},
            (3, "[Kaeltepark] State: Not applicable"),
        ),
        (
            "Pumpe 5",
            {},
            {"Pumpe 5": {"location": "Kaeltepark", "state": ("unknown[5]", 3)}},
            (3, "[Kaeltepark] State: unknown[5]"),
        ),
        (
            "Pumpe without location",
            {},
            {"Pumpe without location": {"location": "", "state": ("unknown[5]", 3)}},
            (3, "State: unknown[5]"),
        ),
    ],
)
def test_apc_netbotz_drycontact_check(item, params, data, expected) -> None:

    check = Check("apc_netbotz_drycontact")
    assert check.run_check(item, params, data) == expected
