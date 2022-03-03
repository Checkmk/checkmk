#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "string_table, section",
    [
        pytest.param(
            [
                ["Ambient Air Temperature Sensor Issue", "Inactive Event"],
                ["Supply Fluid Over Temp", "Inactive Event"],
                ["Supply Fluid Under Temp", "Inactive Event"],
                ["Supply Fluid Temp Sensor Issue", "Active Warning"],
            ],
            {
                "events": {
                    "Ambient Air Temperature Sensor Issue": "Inactive Event",
                    "Supply Fluid Over Temp": "Inactive Event",
                    "Supply Fluid Temp Sensor Issue": "Active Warning",
                    "Supply Fluid Under Temp": "Inactive Event",
                },
            },
            id="Liebert events are parsed correctly",
        ),
        pytest.param(
            [],
            {
                "events": {},
            },
            id="No events lead to an empty 'events' collection",
        ),
    ],
)
def test_parse_liebert_system_events(string_table, section):
    check = Check("liebert_system_events")
    assert check.run_parse(string_table) == section


@pytest.mark.parametrize(
    "string_table, discovered_item",
    [
        pytest.param(
            {
                "events": {
                    "Ambient Air Temperature Sensor Issue": "Inactive Event",
                    "Supply Fluid Over Temp": "Inactive Event",
                    "Supply Fluid Temp Sensor Issue": "Active Warning",
                    "Supply Fluid Under Temp": "Inactive Event",
                },
            },
            [(None, {})],
            id="One service is discovered if there are any events",
        ),
        pytest.param(
            {
                "events": {},
            },
            [(None, {})],
            id="One service is discovered even if there are no events",
        ),
    ],
)
def test_discover_liebert_system_events(string_table, discovered_item):
    check = Check("liebert_system_events")
    assert check.run_discovery(string_table) == discovered_item


@pytest.mark.parametrize(
    "string_table, check_results",
    [
        pytest.param(
            {
                "events": {
                    "Ambient Air Temperature Sensor Issue": "Inactive Event",
                    "Supply Fluid Over Temp": "Inactive Event",
                    "Supply Fluid Temp Sensor Issue": "Active Warning",
                    "Supply Fluid Under Temp": "Inactive Event",
                },
            },
            [(2, "Supply Fluid Temp Sensor Issue: Active Warning")],
            id="State is WARN when there is at least one event with an active warning",
        ),
        pytest.param(
            {
                "events": {},
            },
            [(0, "Normal")],
            id="State is OK when there are no events",
        ),
    ],
)
def test_check_liebert_system_events(string_table, check_results):
    check = Check("liebert_system_events")
    assert list(check.run_check(None, {}, string_table)) == check_results
