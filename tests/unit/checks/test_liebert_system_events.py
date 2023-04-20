#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import Check

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.esx_vsphere import Section

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
def test_parse_liebert_system_events(string_table: StringTable, section: Section) -> None:
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
def test_discover_liebert_system_events(
    string_table: Mapping[str, Mapping[str, str]], discovered_item: Sequence[object]
) -> None:
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
        pytest.param(
            {
                "events": {
                    "Ambient Air Temperature Sensor Issue": "Inactive Event",
                    "Supply Fluid Over Temp": "Inactive Event",
                },
            },
            [(0, "Normal")],
            id="State is OK when there are only incative events",
        ),
    ],
)
def test_check_liebert_system_events(
    string_table: Mapping[str, Mapping[str, str]], check_results: Sequence[tuple[int, str]]
) -> None:
    check = Check("liebert_system_events")
    assert list(check.run_check(None, {}, string_table)) == check_results
