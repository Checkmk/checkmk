#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.innovaphone.agent_based.innovaphone_channels import (
    Channel,
    check_innovaphone_channels,
    discover_innovaphone_channels,
    parse_innovaphone_channels,
)

_PARAMS = {"levels": (75.0, 80.0)}


def test_parse_innovaphone_channels_maps_rows_by_item() -> None:
    string_table = [
        ["Channel A", "Up", "Up", "10", "40"],
        ["Channel B", "Down", "Up", "0", "30"],
    ]

    assert parse_innovaphone_channels(string_table) == {
        "Channel A": Channel(link="Up", physical="Up", idle=10.0, total=40.0),
        "Channel B": Channel(link="Down", physical="Up", idle=0.0, total=30.0),
    }


def test_discover_innovaphone_channels_only_discovers_channels_that_are_up() -> None:
    section = {
        "Up": Channel(link="Up", physical="Up", idle=10.0, total=40.0),
        "Link down": Channel(link="Down", physical="Up", idle=10.0, total=40.0),
        "Physical down": Channel(link="Up", physical="Down", idle=10.0, total=40.0),
    }

    assert list(discover_innovaphone_channels(section)) == [Service(item="Up")]


def test_check_innovaphone_channels_missing_item_yields_nothing() -> None:
    assert not list(check_innovaphone_channels("Missing", _PARAMS, {}))


@pytest.mark.parametrize(
    "link, physical",
    [
        pytest.param("Down", "Up", id="link down"),
        pytest.param("Up", "Down", id="physical down"),
    ],
)
def test_check_innovaphone_channels_down_channel_is_crit(link: str, physical: str) -> None:
    section = {"A": Channel(link=link, physical=physical, idle=10.0, total=40.0)}

    assert list(check_innovaphone_channels("A", _PARAMS, section)) == [
        Result(state=State.CRIT, summary=f"Link: {link}, Physical: {physical}"),
    ]


# fmt: off
@pytest.mark.parametrize(
    "idle, expected_state, expected_usage",
    [
        pytest.param(30.0, State.OK, 25, id="below warn"),
        pytest.param(10.0, State.WARN, 75, id="at warn"),
        pytest.param(8.0, State.CRIT, 80, id="at crit"),
        pytest.param(0.0, State.CRIT, 100, id="fully used"),
    ],
)
# fmt: on
def test_check_innovaphone_channels_usage_state_follows_levels(
    idle: float, expected_state: State, expected_usage: int
) -> None:
    section = {"A": Channel(link="Up", physical="Up", idle=idle, total=40.0)}

    result, metric = check_innovaphone_channels("A", _PARAMS, section)

    assert (result, metric) == (
        Result(
            state=expected_state,
            summary=(
                f"Current: {expected_usage}% (used: {40 - idle:.0f}, free: {idle:.0f}, total: 40)"
            ),
        ),
        Metric("usage", expected_usage, levels=(75.0, 80.0), boundaries=(0, 100)),
    )


def test_check_innovaphone_channels_usage_is_truncated_to_whole_percent() -> None:
    section = {"A": Channel(link="Up", physical="Up", idle=1.0, total=3.0)}

    result, metric = check_innovaphone_channels("A", _PARAMS, section)

    assert (result, metric) == (
        Result(state=State.OK, summary="Current: 66% (used: 2, free: 1, total: 3)"),
        Metric("usage", 66, levels=(75.0, 80.0), boundaries=(0, 100)),
    )
