#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import LevelsT, Result, Service, State
from cmk.plugins.collection.agent_based.f5_bigip_pool import (
    check_f5_bigip_pool,
    f5_bigip_pool_get_down_members,
    inventory_f5_bigip_pool,
    parse_f5_bigip_pool,
    PoolMember,
    Section,
)

StringTable = list[list[str]]


def _make_section(
    active_members: int = 2,
    defined_members: int = 2,
    members_info: list[PoolMember] | None = None,
) -> Mapping[str, Section]:
    return {
        "pool1": Section(
            active_members=active_members,
            defined_members=defined_members,
            members_info=members_info or [],
        )
    }


def test_parse_f5_bigip_pool_member_and_status_blocks() -> None:
    string_table: Sequence[StringTable] = [
        [["pool1", "1", "2"], ["pool2", "2", "2"]],
        [
            ["pool1", "81", "4", "4", "2", "/Common/node1"],
            ["pool2", "82", "4", "28", "2", "/Common/node2"],
        ],
    ]

    result = parse_f5_bigip_pool(string_table)

    assert "pool1" in result
    assert "pool2" in result

    assert result["pool1"].active_members == 1
    assert result["pool1"].defined_members == 2
    assert result["pool1"].members_info == [
        PoolMember(
            port="81",
            monitor_state=4,
            monitor_status=4,
            session_status=2,
            node_name="/Common/node1",
        )
    ]

    assert result["pool2"].active_members == 2
    assert result["pool2"].defined_members == 2
    assert result["pool2"].members_info == [
        PoolMember(
            port="82",
            monitor_state=4,
            monitor_status=28,
            session_status=2,
            node_name="/Common/node2",
        )
    ]


def test_parse_f5_bigip_pool_empty_block() -> None:
    string_table: Sequence[StringTable] = [[]]
    result = parse_f5_bigip_pool(string_table)
    assert result == {}


def test_parse_f5_bigip_pool_break_on_second_member_block() -> None:
    string_table: Sequence[StringTable] = [
        [["pool1", "1", "2"]],
        [["pool2", "2", "2"]],
        [["pool1", "pool1", "4", "4", "2", "/Common/node1"]],
    ]
    result = parse_f5_bigip_pool(string_table)
    assert "pool1" in result
    assert "pool2" not in result


def test_inventory_f5_bigip_pool() -> None:
    section: Mapping[str, Section] = _make_section()
    services = list(inventory_f5_bigip_pool(section))

    assert len(services) == 1
    assert isinstance(services[0], Service)
    assert services[0].item == "pool1"


def test_inventory_f5_bigip_pool_skips_empty_item() -> None:
    section: Mapping[str, Section] = {"": Section(2, 2, [])}
    services = list(inventory_f5_bigip_pool(section))
    assert services == []


@pytest.mark.parametrize(
    "down_info,expected",
    [
        (
            [
                PoolMember(
                    port="80",
                    monitor_state=4,
                    monitor_status=4,
                    session_status=2,
                    node_name="/Common/node1",
                )
            ],
            "node1:80",
        ),
        (
            [
                PoolMember(
                    port="443",
                    monitor_state=4,
                    monitor_status=4,
                    session_status=3,
                    node_name="node2",
                )
            ],
            "node2:443",
        ),
        (
            [
                PoolMember(
                    port="8080",
                    monitor_state=4,
                    monitor_status=4,
                    session_status=1,
                    node_name="/Common/node3",
                )
            ],
            "",
        ),
        (
            [
                PoolMember(
                    port="8081",
                    monitor_state=3,
                    monitor_status=4,
                    session_status=2,
                    node_name="/Common/node4",
                )
            ],
            "node4:8081",
        ),
        (
            [
                PoolMember(
                    port="8082",
                    monitor_state=4,
                    monitor_status=2,
                    session_status=2,
                    node_name="/Common/node5",
                )
            ],
            "node5:8082",
        ),
    ],
)
def test_f5_bigip_pool_get_down_members(down_info: list[PoolMember], expected: str) -> None:
    result = f5_bigip_pool_get_down_members(down_info)
    assert result == expected


@pytest.mark.parametrize(
    "active_members,defined_members,input_lower,expected_state,additional_in_summary",
    [
        (2, 4, (2, 1), State.OK, ""),
        (1, 2, (2, 1), State.WARN, " (warn/crit below 2/1)"),
        (0, 2, (2, 1), State.CRIT, " (warn/crit below 2/1)"),
        (2, 4, (0, 0), State.OK, ""),
        (1, 10, (0, 0), State.OK, ""),
        (2, 2, (0, 0), State.OK, ""),
        (2, 2, (3, 4), State.OK, ""),
    ],
)
def test_check_f5_bigip_pool_states(
    active_members: int,
    defined_members: int,
    input_lower: tuple[int, int],
    expected_state: State,
    additional_in_summary: str,
) -> None:
    expected_in_summary = f"Members up: {active_members}{additional_in_summary}"
    section = _make_section(active_members=active_members, defined_members=defined_members)
    levels_lower: LevelsT = ("fixed", input_lower)
    results = list(check_f5_bigip_pool("pool1", {"levels_lower": levels_lower}, section))

    assert len(results) == 2
    assert isinstance(results[0], Result)
    assert results[0].state == expected_state
    assert expected_in_summary in results[0].summary

    assert isinstance(results[1], Result)
    assert results[1].summary == f"Members total: {defined_members}"


def test_check_f5_bigip_pool_down_members_in_summary() -> None:
    members_info = [
        PoolMember(
            port="80",
            monitor_state=4,
            monitor_status=28,
            session_status=2,
            node_name="/Common/node1",
        )
    ]
    section: Mapping[str, Section] = _make_section(
        active_members=1, defined_members=2, members_info=members_info
    )
    params: Mapping[str, LevelsT] = {"levels_lower": ("fixed", (2, 1))}
    results = list(check_f5_bigip_pool("pool1", params, section))

    assert len(results) == 3
    assert isinstance(results[2], Result)
    assert "down/disabled nodes: node1:80" in results[2].summary


def test_check_f5_bigip_pool_item_not_found() -> None:
    section: Mapping[str, Section] = _make_section()
    params: Mapping[str, LevelsT] = {"levels_lower": ("fixed", (2, 1))}

    results = list(check_f5_bigip_pool("not_a_pool", params, section))

    assert results == []
