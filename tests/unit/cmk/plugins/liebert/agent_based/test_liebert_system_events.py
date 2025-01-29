#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.liebert.agent_based import liebert_system_events as lse


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
def test_parse_liebert_system_events(string_table: StringTable, section: lse.Section) -> None:
    assert lse.parse_liebert_system_events(string_table) == section


@pytest.mark.parametrize(
    "section, discovered_item",
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
            [Service()],
            id="One service is discovered if there are any events",
        ),
        pytest.param(
            {
                "events": {},
            },
            [Service()],
            id="One service is discovered even if there are no events",
        ),
    ],
)
def test_discover_liebert_system_events(
    section: lse.Section, discovered_item: Sequence[Service]
) -> None:
    assert list(lse.discover_liebert_system_events(section)) == discovered_item


@pytest.mark.parametrize(
    "section, check_results",
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
            [Result(state=State.CRIT, summary="Supply Fluid Temp Sensor Issue: Active Warning")],
            id="State is WARN when there is at least one event with an active warning",
        ),
        pytest.param(
            {
                "events": {},
            },
            [Result(state=State.OK, summary="Normal")],
            id="State is OK when there are no events",
        ),
        pytest.param(
            {
                "events": {
                    "Ambient Air Temperature Sensor Issue": "Inactive Event",
                    "Supply Fluid Over Temp": "Inactive Event",
                },
            },
            [Result(state=State.OK, summary="Normal")],
            id="State is OK when there are only incative events",
        ),
    ],
)
def test_check_liebert_system_events(section: lse.Section, check_results: Sequence[Result]) -> None:
    assert list(lse.check_liebert_system_events(section)) == check_results
