#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.legacy_checks import mcafee_emailgateway_entities as plugin


def test_parse_maps_titles_across_all_subtables() -> None:
    section = plugin.parse_mcafee_emailgateway_entities(
        [
            [["0", "1", "0", "0", "0", "0", "0", "0"]],
            [["0"] * 21],
            [["2"] * 6],
        ]
    )
    assert section is not None
    assert section["Voltage"] == "1"
    assert section["NTP"] == "0"
    assert section["RMD Merge"] == "2"


def test_parse_incomplete_returns_none() -> None:
    assert plugin.parse_mcafee_emailgateway_entities([[], [["0"] * 21], [["0"] * 6]]) is None


def test_discover_skips_disabled_and_not_applicable() -> None:
    section = {"Temperature": "0", "Power Supplies": "10", "UPS": "11"}
    discovered = {service.item for service in plugin.discover_mcafee_emailgateway_entities(section)}
    assert discovered == {"Temperature"}


@pytest.mark.parametrize(
    "dev_state, expected_state, expected_readable",
    [
        ("0", State.OK, "healthy"),
        ("2", State.WARN, "requires attention"),
        ("8", State.CRIT, "critical"),
        ("9", State.UNKNOWN, "unknown state"),
    ],
)
def test_check(dev_state: str, expected_state: State, expected_readable: str) -> None:
    assert list(
        plugin.check_mcafee_emailgateway_entities("Temperature", {"Temperature": dev_state})
    ) == [Result(state=expected_state, summary=f"Status: {expected_readable}")]


def test_check_missing_item() -> None:
    assert list(plugin.check_mcafee_emailgateway_entities("Missing", {"Temperature": "0"})) == []
