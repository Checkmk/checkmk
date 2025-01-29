#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.collection.agent_based.cisco_wlc import (
    check_cisco_wlc,
    cluster_check_cisco_wlc,
    discovery_cisco_wlc,
    parse_cisco_wlc,
    Section,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[["AP19", "1"], ["AP02", "1"]]], {"AP19": "1", "AP02": "1"}),
    ],
)
def test_parse_cisco_wlc(string_table: list[StringTable], expected_parsed_data: Section) -> None:
    assert parse_cisco_wlc(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,services",
    [
        (
            {"AP19": "1", "AP02": "1"},
            [
                Service(item="AP19"),
                Service(item="AP02"),
            ],
        ),
    ],
)
def test_discovery_cisco_wlc(section: Section, services: DiscoveryResult) -> None:
    assert list(discovery_cisco_wlc(section)) == services


@pytest.mark.parametrize(
    "item,params,section,results",
    [
        (
            "AP19",
            {},
            {"AP19": "1", "AP02": "1"},
            [Result(state=State.OK, summary="Accesspoint: online")],
        ),
        (
            "AP18",
            {},
            {"AP19": "1", "AP02": "1"},
            [Result(state=State.CRIT, summary="Accesspoint not found")],
        ),
    ],
)
def test_check_cisco_wlc(
    item: str, params: Mapping[str, object], section: Section, results: CheckResult
) -> None:
    assert list(check_cisco_wlc(item, params, section)) == results


@pytest.mark.parametrize(
    "item,params,section,result",
    [
        (
            "AP19",
            {},
            {"node1": {"AP19": "1", "AP02": "1"}},
            [Result(state=State.OK, summary="Accesspoint: online (connected to node1)")],
        ),
        (
            "AP18",
            {},
            {"node1": {"AP19": "1", "AP02": "1"}},
            [Result(state=State.CRIT, summary="Accesspoint not found")],
        ),
    ],
)
def test_cluster_check_cisco_wlc(
    item: str,
    params: Mapping[str, object],
    section: Mapping[str, Section | None],
    result: CheckResult,
) -> None:
    assert list(cluster_check_cisco_wlc(item, params, section)) == result
