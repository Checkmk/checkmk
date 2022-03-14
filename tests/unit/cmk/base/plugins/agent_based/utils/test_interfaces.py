#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.utils import interfaces

CheckResults = Sequence[Union[Result, Metric, IgnoreResults]]


def _create_interfaces(
    bandwidth_change: int,
    **kwargs: Any,
) -> interfaces.Section:
    ifaces = [
        interfaces.Interface(
            "1",
            "lo",
            "lo",
            "24",
            0,
            "1",
            266045395,
            97385,
            0,
            0,
            0,
            0,
            266045395,
            97385,
            0,
            0,
            0,
            0,
            0,
            "\x00\x00\x00\x00\x00\x00",
        ),
        interfaces.Interface(
            "2",
            "docker0",
            "docker0",
            "6",
            0,
            "2",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            "\x02B\x9d\xa42/",
        ),
        interfaces.Interface(
            "3",
            "enp0s31f6",
            "enp0s31f6",
            "6",
            0,
            "2",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            "\xe4\xb9z6\x93\xad",
        ),
        interfaces.Interface(
            "4",
            "enxe4b97ab99f99",
            "enxe4b97ab99f99",
            "6",
            10000000,
            "2",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            "\xe4\xb9z\xb9\x9f\x99",
        ),
        interfaces.Interface(
            "5",
            "vboxnet0",
            "vboxnet0",
            "6",
            10000000,
            "1",
            0,
            0,
            0,
            0,
            0,
            0,
            20171,
            113,
            0,
            0,
            0,
            0,
            0,
            "\n\x00'\x00\x00\x00",
        ),
        interfaces.Interface(
            "6",
            "wlp2s0",
            "wlp2s0",
            "6",
            0,
            "1",
            346922243 + bandwidth_change,
            244867,
            0,
            0,
            0,
            0,
            6570143 + 4 * bandwidth_change,
            55994,
            0,
            0,
            0,
            0,
            0,
            "d]\x86\xe4P/",
        ),
    ]
    for iface in ifaces:
        for k, v in kwargs.items():
            setattr(iface, k, v)
    return ifaces


def _add_node_name_to_results(
    results: CheckResults,
    node_name: str,
) -> CheckResults:
    res = results[0]
    assert isinstance(res, Result)
    return [
        Result(  # type: ignore[call-overload]
            state=res.state,
            summary=f"{res.summary} on {node_name}" if res.summary else None,
            notice=f"{res.details} on {node_name}" if not res.summary else None,
            details=f"{res.details} on {node_name}" if res.details else None,
        ),
        *results[1:],
    ]


def _add_group_info_to_results(
    results: CheckResults,
    members: str,
) -> CheckResults:
    return [
        Result(
            state=State.OK,
            summary="Interface group",
        ),
        Result(
            state=State.OK,
            summary="(up)",
            details="Operational state: up",
        ),
        results[2],
        Result(
            state=State.OK,
            summary=members,
        ),
        *results[3:],
    ]


DEFAULT_DISCOVERY_PARAMS = interfaces.DISCOVERY_DEFAULT_PARAMETERS

SINGLE_SERVICES = [
    Service(
        item="5",
        parameters={"discovered_oper_status": ["1"], "discovered_speed": 10000000},
    ),
    Service(
        item="6",
        parameters={"discovered_oper_status": ["1"], "discovered_speed": 0},
    ),
]


def test_discovery_ungrouped_all() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [DEFAULT_DISCOVERY_PARAMS],
                _create_interfaces(0),
            )
        )
        == SINGLE_SERVICES
    )


def test_discovery_ungrouped_empty_section() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [
                    {
                        "discovery_single": (
                            True,
                            {
                                "item_appearance": "alias",
                                "pad_portnumbers": True,
                            },
                        ),
                        "matching_conditions": (True, {}),
                    },
                    DEFAULT_DISCOVERY_PARAMS,
                ],
                [],
            )
        )
        == []
    )


def test_discovery_ungrouped_admin_status() -> None:
    ifaces = _create_interfaces(0, admin_status="1")
    ifaces[-1].admin_status = "2"
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "discovery_single": (
                        False,
                        {},
                    ),
                    "matching_conditions": (
                        False,
                        {"admin_states": ["2"]},
                    ),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            ifaces,
        )
    ) == [
        Service(
            item="5",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
                "discovered_admin_status": ["1"],
            },
            labels=[],
        ),
    ]


def test_discovery_ungrouped_one() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [
                    {
                        "matching_conditions": (
                            False,
                            {
                                "match_index": ["5"],
                            },
                        ),
                        "discovery_single": (False, {}),
                    },
                    DEFAULT_DISCOVERY_PARAMS,
                ],
                _create_interfaces(0),
            )
        )
        == SINGLE_SERVICES[1:]
    )


def test_discovery_ungrouped_off() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [
                    {
                        "matching_conditions": (True, {}),
                        "discovery_single": (False, {}),
                    },
                    DEFAULT_DISCOVERY_PARAMS,
                ],
                _create_interfaces(0),
            )
        )
        == []
    )


def test_discovery_duplicate_index() -> None:
    assert list(
        interfaces.discover_interfaces(
            [DEFAULT_DISCOVERY_PARAMS],
            _create_interfaces(0, index="1"),
        )
    ) == [
        Service(
            item="1",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
    ]


def test_discovery_duplicate_descr() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    **DEFAULT_DISCOVERY_PARAMS,
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "descr",
                            "pad_portnumbers": True,
                        },
                    ),
                }
            ],
            _create_interfaces(0, descr="description"),
        )
    ) == [
        Service(
            item="description 5",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="description 6",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
            },
            labels=[],
        ),
    ]


def test_discovery_duplicate_alias() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "alias",
                            "pad_portnumbers": True,
                        },
                    ),
                    "matching_conditions": (
                        False,
                        {
                            "match_index": ["5"],
                        },
                    ),
                }
            ],
            _create_interfaces(0, alias="alias"),
        )
    ) == [
        Service(
            item="alias 5",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
    ]


def test_discovery_partial_duplicate_desc_duplicate_alias() -> None:
    ifaces = _create_interfaces(0)
    ifaces[3].descr = "duplicate_descr"
    ifaces[4].descr = "duplicate_descr"
    for iface in ifaces:
        iface.alias = "alias"
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "descr",
                            "pad_portnumbers": True,
                        },
                    ),
                    "matching_conditions": (
                        False,
                        {
                            "match_index": ["4", "5", "6"],
                        },
                    ),
                }
            ],
            ifaces,
        )
    ) == [
        Service(
            item="duplicate_descr 4",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="duplicate_descr 5",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="wlp2s0",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_simple() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "matching_conditions": (True, {}),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "group",
                                    "member_appearance": "index",
                                }
                            ],
                        },
                    ),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )
    ) == SINGLE_SERVICES + [
        Service(
            item="group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                    "inclusion_condition": {},
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_hierarchy() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "matching_conditions": (
                        False,
                        {
                            "portstates": ["1", "2"],
                        },
                    ),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "group",
                                    "member_appearance": "alias",
                                }
                            ],
                        },
                    ),
                },
                {
                    "matching_conditions": (True, {}),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "group",
                                    "member_appearance": "index",
                                }
                            ],
                        },
                    ),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )
    ) == SINGLE_SERVICES + [
        Service(
            item="group",
            parameters={
                "aggregate": {
                    "member_appearance": "alias",
                    "inclusion_condition": {"portstates": ["1", "2"]},
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_exclusion_condition() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "matching_conditions": (
                        False,
                        {
                            "match_desc": ["eth"],
                        },
                    ),
                    "grouping": (
                        False,
                        {
                            "group_items": [],
                        },
                    ),
                },
                {
                    "matching_conditions": (True, {}),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "group",
                                    "member_appearance": "index",
                                }
                            ],
                        },
                    ),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )
    ) == SINGLE_SERVICES + [
        Service(
            item="group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                    "inclusion_condition": {},
                    "exclusion_conditions": [{"match_desc": ["eth"]}],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_empty() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [
                    {
                        "matching_conditions": (
                            False,
                            {
                                "match_desc": ["non_existing"],
                            },
                        ),
                        "grouping": (
                            True,
                            {
                                "group_items": [
                                    {
                                        "group_name": "group",
                                        "member_appearance": "index",
                                    }
                                ],
                            },
                        ),
                    },
                    DEFAULT_DISCOVERY_PARAMS,
                ],
                _create_interfaces(0),
            )
        )
        == SINGLE_SERVICES
    )


def test_discovery_grouped_by_agent() -> None:
    ifaces = _create_interfaces(0)
    ifaces[0].group = "group"
    ifaces[1].group = "group"
    assert list(
        interfaces.discover_interfaces(
            [DEFAULT_DISCOVERY_PARAMS],
            ifaces,
        )
    ) == SINGLE_SERVICES + [
        Service(
            item="group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 0.0,
            },
            labels=[],
        ),
    ]


def test_discovery_grouped_by_agent_and_in_rules() -> None:
    ifaces = _create_interfaces(0)
    ifaces[0].group = "group"
    ifaces[1].group = "group"
    assert list(
        interfaces.discover_interfaces(
            [
                (
                    {
                        "matching_conditions": (True, {}),
                        "grouping": (
                            True,
                            {
                                "group_items": [
                                    {
                                        "group_name": "group",
                                        "member_appearance": "index",
                                    }
                                ],
                            },
                        ),
                    }
                ),
                DEFAULT_DISCOVERY_PARAMS,
            ],
            ifaces,
        )
    ) == SINGLE_SERVICES + [
        Service(
            item="group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                    "inclusion_condition": {},
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000.0,
            },
            labels=[],
        ),
    ]


def test_discovery_labels() -> None:
    assert list(
        interfaces.discover_interfaces(
            [
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "alias",
                            "pad_portnumbers": True,
                            "labels": {"single": "wlp"},
                        },
                    ),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "wlp_group",
                                    "member_appearance": "index",
                                }
                            ],
                            "labels": {"group": "wlp"},
                        },
                    ),
                    "matching_conditions": (False, {"match_desc": ["wlp"]}),
                },
                {
                    "discovery_single": (
                        True,
                        {
                            "item_appearance": "alias",
                            "pad_portnumbers": True,
                            "labels": {"single": "default"},
                        },
                    ),
                    "grouping": (
                        True,
                        {
                            "group_items": [
                                {
                                    "group_name": "default_group",
                                    "member_appearance": "index",
                                }
                            ],
                            "labels": {"group": "default"},
                        },
                    ),
                    "matching_conditions": (True, {}),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces(0),
        )
    ) == [
        Service(
            item="lo",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 0},
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="docker0",
            parameters={"discovered_oper_status": ["2"], "discovered_speed": 0},
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="enp0s31f6",
            parameters={"discovered_oper_status": ["2"], "discovered_speed": 0},
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="enxe4b97ab99f99",
            parameters={"discovered_oper_status": ["2"], "discovered_speed": 10000000},
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="vboxnet0",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 10000000},
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="wlp2s0",
            parameters={"discovered_oper_status": ["1"], "discovered_speed": 0},
            labels=[ServiceLabel("single", "wlp")],
        ),
        Service(
            item="default_group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                    "inclusion_condition": {},
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 20000000.0,
            },
            labels=[ServiceLabel("group", "default")],
        ),
        Service(
            item="wlp_group",
            parameters={
                "aggregate": {
                    "member_appearance": "index",
                    "inclusion_condition": {"match_desc": ["wlp"]},
                    "exclusion_conditions": [],
                },
                "discovered_oper_status": ["1"],
                "discovered_speed": 0.0,
            },
            labels=[ServiceLabel("group", "wlp")],
        ),
    ]


ITEM_PARAMS_RESULTS = (
    (
        "5",
        {
            "errors": {"both": ("abs", (10, 20))},
            "speed": 10_000_000,
            "traffic": [
                ("both", ("upper", ("perc", (5.0, 20.0)))),
            ],
            "state": ["1"],
        },
        [
            Result(state=State.OK, summary="[vboxnet0]"),
            Result(state=State.OK, summary="(up)", details="Operational state: up"),
            Result(state=State.OK, summary="MAC: 0A:00:27:00:00:00"),
            Result(state=State.OK, summary="Speed: 10 MBit/s"),
            Metric("outqlen", 0.0),
            Result(state=State.OK, summary="In: 0.00 B/s (0%)"),
            Metric("in", 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Result(state=State.OK, summary="Out: 0.00 B/s (0%)"),
            Metric("out", 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Result(state=State.OK, notice="Errors in: 0 packets/s"),
            Metric("inerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast in: 0 packets/s"),
            Metric("inmcast", 0.0),
            Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
            Metric("inbcast", 0.0),
            Result(state=State.OK, notice="Unicast in: 0 packets/s"),
            Metric("inucast", 0.0),
            Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
            Metric("innucast", 0.0),
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast out: 0 packets/s"),
            Metric("outmcast", 0.0),
            Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
            Metric("outbcast", 0.0),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
            Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
            Metric("outnucast", 0.0),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0),
        ],
    ),
    (
        "6",
        {
            "errors": {"both": ("abs", (10, 20))},
            "speed": 100_000_000,
            "traffic": [
                ("both", ("upper", ("perc", (5.0, 20.0)))),
            ],
            "total_traffic": {},
            "state": ["1"],
        },
        [
            Result(state=State.OK, summary="[wlp2s0]"),
            Result(state=State.OK, summary="(up)", details="Operational state: up"),
            Result(state=State.OK, summary="MAC: 64:5D:86:E4:50:2F"),
            Result(state=State.OK, summary="Speed: 100 MBit/s (assumed)"),
            Metric("outqlen", 0.0),
            Result(
                state=State.WARN, summary="In: 800 kB/s (warn/crit at 625 kB/s/2.50 MB/s) (6.40%)"
            ),
            Metric("in", 800000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Result(
                state=State.CRIT,
                summary="Out: 3.20 MB/s (warn/crit at 625 kB/s/2.50 MB/s) (25.60%)",
            ),
            Metric("out", 3200000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Result(state=State.OK, summary="Total: 4.00 MB/s (16.00%)"),
            Metric("total", 4000000.0, boundaries=(0.0, 25000000.0)),
            Result(state=State.OK, notice="Errors in: 0 packets/s"),
            Metric("inerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast in: 0 packets/s"),
            Metric("inmcast", 0.0),
            Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
            Metric("inbcast", 0.0),
            Result(state=State.OK, notice="Unicast in: 0 packets/s"),
            Metric("inucast", 0.0),
            Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
            Metric("innucast", 0.0),
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast out: 0 packets/s"),
            Metric("outmcast", 0.0),
            Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
            Metric("outbcast", 0.0),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
            Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
            Metric("outnucast", 0.0),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0),
        ],
    ),
    (
        "6",
        {
            "errors": {"both": ("abs", (10, 20))},
            "speed": 100000000,
            "traffic": [("both", ("upper", ("perc", (5.0, 20.0))))],
            "state": ["1"],
            "nucasts": (1, 2),
            "discards": (1, 2),
        },
        [
            Result(state=State.OK, summary="[wlp2s0]"),
            Result(state=State.OK, summary="(up)", details="Operational state: up"),
            Result(state=State.OK, summary="MAC: 64:5D:86:E4:50:2F"),
            Result(state=State.OK, summary="Speed: 100 MBit/s (assumed)"),
            Metric("outqlen", 0.0),
            Result(
                state=State.WARN, summary="In: 800 kB/s (warn/crit at 625 kB/s/2.50 MB/s) (6.40%)"
            ),
            Metric("in", 800000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Result(
                state=State.CRIT,
                summary="Out: 3.20 MB/s (warn/crit at 625 kB/s/2.50 MB/s) (25.60%)",
            ),
            Metric("out", 3200000.0, levels=(625000.0, 2500000.0), boundaries=(0.0, 12500000.0)),
            Result(state=State.OK, notice="Errors in: 0 packets/s"),
            Metric("inerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast in: 0 packets/s"),
            Metric("inmcast", 0.0),
            Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
            Metric("inbcast", 0.0),
            Result(state=State.OK, notice="Unicast in: 0 packets/s"),
            Metric("inucast", 0.0),
            Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
            Metric("innucast", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Multicast out: 0 packets/s"),
            Metric("outmcast", 0.0),
            Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
            Metric("outbcast", 0.0),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
            Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
            Metric("outnucast", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0, levels=(1.0, 2.0)),
        ],
    ),
)


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                timestamp=0,
            )
        )
    assert (
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(4000000)[int(item) - 1],
                timestamp=5,
            )
        )
        == result
    )


def test_check_single_interface_same_index_descr_alias() -> None:
    item = "07"
    result = next(  # type: ignore[call-overload]
        interfaces.check_single_interface(
            item,
            {},
            _create_interfaces(0, index=item, descr=item, alias=item)[0],
        )
    )
    assert result == Result(
        state=State.OK,
        summary="(up)",
        details="Operational state: up",
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_admin_status(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    params = {
        **params,
        "discovered_admin_status": "1",
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0, admin_status="1")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000, admin_status="1")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        *result[:2],
        Result(state=State.OK, summary="Admin state: up"),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_states(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": ["4"],
                    "admin_state": ["2"],
                },
                _create_interfaces(0, admin_status="1")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state": ["4"],
                "admin_state": ["2"],
            },
            _create_interfaces(4000000, admin_status="1")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        result[0],
        Result(state=State.CRIT, summary="(up)", details="Operational state: up"),
        Result(state=State.CRIT, summary="Admin state: up"),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_map_states_independently(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state_mappings": (
                        "independent_mappings",
                        {
                            "map_operstates": [(["1"], 3)],
                            "map_admin_states": [(["2"], 3)],
                        },
                    ),
                },
                _create_interfaces(0, admin_status="2")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state_mappings": (
                    "independent_mappings",
                    {
                        "map_operstates": [(["1"], 3)],
                        "map_admin_states": [(["2"], 3)],
                    },
                ),
            },
            _create_interfaces(4000000, admin_status="2")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        result[0],
        Result(state=State.UNKNOWN, summary="(up)", details="Operational state: up"),
        Result(state=State.UNKNOWN, summary="Admin state: down"),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_map_states_combined_matching(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": ["4"],
                    "admin_state": ["1"],
                    "state_mappings": (
                        "combined_mappings",
                        [
                            ("1", "2", 3),
                            ("5", "2", 3),
                            ("2", "2", 2),
                        ],
                    ),
                },
                _create_interfaces(0, admin_status="2")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state": ["4"],
                "admin_state": ["1"],
                "state_mappings": (
                    "combined_mappings",
                    [
                        ("1", "2", 3),
                        ("5", "2", 3),
                        ("2", "2", 2),
                    ],
                ),
            },
            _create_interfaces(4000000, admin_status="2")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        result[0],
        Result(
            state=State.UNKNOWN,
            summary="(op. state: up, admin state: down)",
            details="Operational state: up, Admin state: down",
        ),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_map_states_combined_not_matching(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state_mappings": (
                        "combined_mappings",
                        [
                            ("1", "2", 3),
                            ("5", "2", 3),
                            ("2", "2", 2),
                        ],
                    ),
                },
                _create_interfaces(0, admin_status="3")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state_mappings": (
                    "combined_mappings",
                    [
                        ("1", "2", 3),
                        ("5", "2", 3),
                        ("2", "2", 2),
                    ],
                ),
            },
            _create_interfaces(4000000, admin_status="3")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        result[0],
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="Admin state: testing"),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_map_states_combined_not_matching_with_target_states(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": ["4"],
                    "admin_state": ["1"],
                    "state_mappings": (
                        "combined_mappings",
                        [
                            ("1", "2", 3),
                            ("5", "2", 3),
                            ("2", "2", 2),
                        ],
                    ),
                },
                _create_interfaces(0, admin_status="3")[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state": ["4"],
                "admin_state": ["1"],
                "state_mappings": (
                    "combined_mappings",
                    [
                        ("1", "2", 3),
                        ("5", "2", 3),
                        ("2", "2", 2),
                    ],
                ),
            },
            _create_interfaces(4000000, admin_status="3")[int(item) - 1],
            timestamp=5,
        )
    ) == [
        result[0],
        Result(state=State.CRIT, summary="(up)", details="Operational state: up"),
        Result(state=State.CRIT, summary="Admin state: testing"),
        *result[2:],
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_ignore_state(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": None,
                },
                _create_interfaces(0, oper_status=4)[int(item) - 1],
                timestamp=0,
            )
        )
    assert (
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": None,
                },
                _create_interfaces(4000000, oper_status=4)[int(item) - 1],
                timestamp=5,
            )
        )
        == result
    )


@pytest.mark.parametrize(
    "item, params, result",
    [
        (
            ITEM_PARAMS_RESULTS[0][0],
            ITEM_PARAMS_RESULTS[0][1],
            ITEM_PARAMS_RESULTS[0][2][:5]
            + [
                Result(state=State.OK, summary="In average 5min: 0.00 B/s (0%)"),
            ]
            + [ITEM_PARAMS_RESULTS[0][2][6]]
            + [
                Result(state=State.OK, summary="Out average 5min: 0.00 B/s (0%)"),
            ]
            + ITEM_PARAMS_RESULTS[0][2][8:],
        ),
        (
            ITEM_PARAMS_RESULTS[1][0],
            ITEM_PARAMS_RESULTS[1][1],
            ITEM_PARAMS_RESULTS[1][2][:5]
            + [
                Result(
                    state=State.WARN,
                    summary="In average 5min: 800 kB/s (warn/crit at 625 kB/s/2.50 MB/s) (6.40%)",
                ),
            ]
            + [ITEM_PARAMS_RESULTS[1][2][6]]
            + [
                Result(
                    state=State.CRIT,
                    summary="Out average 5min: 3.20 MB/s (warn/crit at 625 kB/s/2.50 MB/s) (25.60%)",
                ),
            ]
            + [ITEM_PARAMS_RESULTS[1][2][8]]
            + [
                Result(
                    state=State.OK,
                    summary="Total average 5min: 4.00 MB/s (16.00%)",
                ),
            ]
            + ITEM_PARAMS_RESULTS[1][2][10:],
        ),
    ],
)
def test_check_single_interface_averaging(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                timestamp=0,
            )
        )
    assert (
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "average": 5,
                },
                _create_interfaces(4000000)[int(item) - 1],
                timestamp=5,
            )
        )
        == result
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    group_members: interfaces.GroupMembers = {
        None: [
            {"name": "vboxnet0", "oper_status_name": "up"},
            {"name": "wlp2s0", "oper_status_name": "up"},
        ]
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                group_members=group_members,
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            group_members=group_members,
            timestamp=5,
        )
    ) == _add_group_info_to_results(result, "Members: [vboxnet0 (up), wlp2s0 (up)]")


@pytest.mark.parametrize(
    "item, params",
    [
        (
            item,
            params,
        )
        for item, params, _results in ITEM_PARAMS_RESULTS
    ],
)
def test_check_single_interface_input_is_rate(
    item: str,
    params: Mapping[str, Any],
) -> None:
    # check that this does not raise an IgnoreResultsError, since no rates are computed
    list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(0)[int(item) - 1],
            input_is_rate=True,
        )
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group_admin_status(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    group_members: interfaces.GroupMembers = {
        None: [
            {"name": "vboxnet0", "oper_status_name": "up", "admin_status_name": "down"},
            {"name": "wlp2s0", "oper_status_name": "up", "admin_status_name": "testing"},
        ]
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                group_members=group_members,
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            group_members=group_members,
            timestamp=5,
        )
    ) == _add_group_info_to_results(
        result,
        "Members: [vboxnet0 (op. state: up, admin state: down), wlp2s0 (op. state: up, "
        "admin state: testing)]",
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_w_node(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    node_name = "node"
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0, node=node_name)[int(item) - 1],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000, node=node_name)[int(item) - 1],
            timestamp=5,
        )
    ) == _add_node_name_to_results(result, node_name)


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group_w_nodes(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    group_members: interfaces.GroupMembers = {
        "node1": [
            {"name": "vboxnet0", "oper_status_name": "up"},
            {"name": "wlp2s0", "oper_status_name": "up"},
        ],
        "node2": [
            {"name": "vboxnet0", "oper_status_name": "up"},
            {"name": "wlp2s0", "oper_status_name": "up"},
        ],
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces(0)[int(item) - 1],
                group_members=group_members,
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces(4000000)[int(item) - 1],
            group_members=group_members,
            timestamp=5,
        )
    ) == _add_group_info_to_results(
        result,
        "Members: [vboxnet0 (up), wlp2s0 (up) on node node1] [vboxnet0 (up), wlp2s0 (up) on node "
        "node2]",
    )


def test_check_single_interface_packet_levels():
    assert list(
        interfaces.check_single_interface(
            "1",
            {
                "errors": {
                    "both": ("abs", (10, 20)),
                },
                "nucasts": (0, 5),
                "unicast": {
                    "in": ("perc", (10.0, 20.0)),
                    "out": ("perc", (10.0, 20.0)),
                },
                "multicast": {
                    "in": ("abs", (11, 23)),
                    "out": ("perc", (10.0, 20.0)),
                },
                "broadcast": {
                    "both": ("perc", (0.0, 2.0)),
                },
                "discards": (50.0, 300.0),
            },
            _create_interfaces(
                0,
                in_ucast=10,
                in_mcast=20,
                in_bcast=30,
                in_discards=40,
                in_errors=50,
                out_ucast=60,
                out_mcast=70,
                out_bcast=80,
                out_discards=90,
                out_errors=100,
            )[0],
            input_is_rate=True,
        )
    ) == [
        Result(
            state=State.OK,
            summary="[lo]",
        ),
        Result(
            state=State.OK,
            summary="(up)",
            details="Operational state: up",
        ),
        Result(
            state=State.OK,
            summary="MAC: 00:00:00:00:00:00",
        ),
        Result(
            state=State.OK,
            summary="Speed: unknown",
        ),
        Metric(
            "outqlen",
            0.0,
        ),
        Result(
            state=State.OK,
            summary="In: 266 MB/s",
        ),
        Metric(
            "in",
            266045395.0,
            boundaries=(0.0, None),
        ),
        Result(
            state=State.OK,
            summary="Out: 266 MB/s",
        ),
        Metric(
            "out",
            266045395.0,
            boundaries=(0.0, None),
        ),
        Result(
            state=State.CRIT,
            summary="Errors in: 50 packets/s (warn/crit at 10 packets/s/20 packets/s)",
        ),
        Metric(
            "inerr",
            50.0,
            levels=(10.0, 20.0),
        ),
        Result(
            state=State.WARN,
            summary="Multicast in: 20 packets/s (warn/crit at 11 packets/s/23 packets/s)",
        ),
        Metric(
            "inmcast",
            20.0,
            levels=(11.0, 23.0),
        ),
        Result(
            state=State.CRIT,
            summary="Broadcast in: 50% (warn/crit at 0%/2%)",
        ),
        Metric(
            "inbcast",
            30.0,
            levels=(0.0, 1.2),
        ),
        Result(
            state=State.WARN,
            summary="Unicast in: 16.667% (warn/crit at 10%/20%)",
        ),
        Metric(
            "inucast",
            10.0,
            levels=(6.0, 12.0),
        ),
        Result(
            state=State.CRIT,
            summary="Non-unicast in: 50 packets/s (warn/crit at 0 packets/s/5 packets/s)",
        ),
        Metric(
            "innucast",
            50.0,
            levels=(0.0, 5.0),
        ),
        Result(
            state=State.OK,
            notice="Discards in: 40 packets/s",
        ),
        Metric(
            "indisc",
            40.0,
            levels=(50.0, 300.0),
        ),
        Result(
            state=State.CRIT,
            summary="Errors out: 100 packets/s (warn/crit at 10 packets/s/20 packets/s)",
        ),
        Metric(
            "outerr",
            100.0,
            levels=(10.0, 20.0),
        ),
        Result(
            state=State.CRIT,
            summary="Multicast out: 33.333% (warn/crit at 10%/20%)",
        ),
        Metric(
            "outmcast",
            70.0,
            levels=(21.0, 42.0),
        ),
        Result(
            state=State.CRIT,
            summary="Broadcast out: 38.095% (warn/crit at 0%/2%)",
        ),
        Metric(
            "outbcast",
            80.0,
            levels=(0.0, 4.2),
        ),
        Result(
            state=State.CRIT,
            summary="Unicast out: 28.571% (warn/crit at 10%/20%)",
        ),
        Metric(
            "outucast",
            60.0,
            levels=(21.0, 42.0),
        ),
        Result(
            state=State.CRIT,
            summary="Non-unicast out: 150 packets/s (warn/crit at 0 packets/s/5 packets/s)",
        ),
        Metric(
            "outnucast",
            150.0,
            levels=(0.0, 5.0),
        ),
        Result(
            state=State.WARN,
            summary="Discards out: 90 packets/s (warn/crit at 50 packets/s/300 packets/s)",
        ),
        Metric(
            "outdisc",
            90.0,
            levels=(50.0, 300.0),
        ),
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0),
                timestamp=0,
            )
        )
    assert (
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(4000000),
                timestamp=5,
            )
        )
        == result
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_descr(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    description = "description"
    item = "%s %s" % (description, item)
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0, descr=description),
                timestamp=0,
            )
        )
    assert (
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(4000000, descr=description),
                timestamp=5,
            )
        )
        == result
    )


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_alias(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    alias = "alias"
    index = item
    item = "%s %s" % (alias, index)
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0, alias=alias),
                timestamp=0,
            )
        )
    ifaces = _create_interfaces(4000000, alias=alias)
    assert list(interfaces.check_multiple_interfaces(item, params, ifaces, timestamp=5,)) == [
        Result(
            state=State.OK,
            summary="[%s/%s]" % (alias, ifaces[int(index) - 1].descr),
        ),
        *result[1:],
    ]


def test_check_multiple_interfaces_group_simple() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("upper", ("perc", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("upper", ("perc", (10.0, 30.0))),
            ]
        },
        "aggregate": {
            "member_appearance": "index",
            "inclusion_condition": {},
            "exclusion_conditions": [],
        },
        "discovered_oper_status": ["1"],
        "discovered_speed": 20000000,
        "state": ["8"],
        "speed": 123456,
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                "group",
                params,
                _create_interfaces(0),
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            _create_interfaces(4000000),
            timestamp=5,
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.OK, summary="(degraded)", details="Operational state: degraded"),
        Result(
            state=State.OK,
            summary="Members: [1 (up), 2 (down), 3 (down), 4 (down), 5 (up), 6 (up)]",
        ),
        Result(state=State.WARN, summary="Speed: 10 MBit/s (expected: 123 kBit/s)"),
        Metric("outqlen", 0.0),
        Result(state=State.CRIT, summary="In: 800 kB/s (warn/crit at 62.5 kB/s/250 kB/s) (64.00%)"),
        Metric("in", 800000.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
        Result(
            state=State.CRIT, summary="Out: 3.20 MB/s (warn/crit at 62.5 kB/s/250 kB/s) (256.00%)"
        ),
        Metric("out", 3200000.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
        Result(
            state=State.CRIT, summary="Total: 4.00 MB/s (warn/crit at 250 kB/s/750 kB/s) (160.00%)"
        ),
        Metric("total", 4000000.0, levels=(250000.0, 750000.0), boundaries=(0.0, 2500000.0)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]


def test_check_multiple_interfaces_group_exclude() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("upper", ("perc", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("upper", ("perc", (10.0, 30.0))),
            ]
        },
        "aggregate": {
            "member_appearance": "index",
            "inclusion_condition": {},
            "exclusion_conditions": [{"match_index": ["4", "5"]}],
        },
        "discovered_oper_status": ["1"],
        "discovered_speed": 20000000,
    }
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                "group",
                params,
                _create_interfaces(0),
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            _create_interfaces(4000000),
            timestamp=5,
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.CRIT, summary="(degraded)", details="Operational state: degraded"),
        Result(state=State.OK, summary="Members: [1 (up), 2 (down), 3 (down), 6 (up)]"),
        Result(state=State.OK, summary="Speed: 20 MBit/s (assumed)"),
        Metric("outqlen", 0.0),
        Result(state=State.CRIT, summary="In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.00%)"),
        Metric("in", 800000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.00%)"
        ),
        Metric("out", 3200000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Total: 4.00 MB/s (warn/crit at 500 kB/s/1.50 MB/s) (80.00%)"
        ),
        Metric("total", 4000000.0, levels=(500000.0, 1500000.0), boundaries=(0.0, 5000000.0)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]


def test_check_multiple_interfaces_group_by_agent() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("upper", ("perc", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("upper", ("perc", (10.0, 30.0))),
            ]
        },
        "aggregate": {
            "member_appearance": "index",
        },
        "discovered_oper_status": ["1"],
        "discovered_speed": 20000000,
    }
    with pytest.raises(IgnoreResultsError):
        ifaces = _create_interfaces(0)
        ifaces[3].group = "group"
        ifaces[5].group = "group"
        list(
            interfaces.check_multiple_interfaces(
                "group",
                params,
                ifaces,
                timestamp=0,
            )
        )

    ifaces = _create_interfaces(4000000)
    ifaces[3].group = "group"
    ifaces[5].group = "group"
    assert list(interfaces.check_multiple_interfaces("group", params, ifaces, timestamp=5,)) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.CRIT, summary="(degraded)", details="Operational state: degraded"),
        Result(state=State.OK, summary="Members: [4 (down), 6 (up)]"),
        Result(state=State.OK, summary="Speed: 20 MBit/s (assumed)"),
        Metric("outqlen", 0.0),
        Result(state=State.CRIT, summary="In: 800 kB/s (warn/crit at 125 kB/s/500 kB/s) (32.00%)"),
        Metric("in", 800000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Out: 3.20 MB/s (warn/crit at 125 kB/s/500 kB/s) (128.00%)"
        ),
        Metric("out", 3200000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Total: 4.00 MB/s (warn/crit at 500 kB/s/1.50 MB/s) (80.00%)"
        ),
        Metric("total", 4000000.0, levels=(500000.0, 1500000.0), boundaries=(0.0, 5000000.0)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_w_node(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    node_name = "node"
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                _create_interfaces(0, node=node_name),
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            _create_interfaces(4000000, node=node_name),
            timestamp=5,
        )
    ) == _add_node_name_to_results(result, node_name)


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_same_item_twice_cluster(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    node_name_1 = "node1"
    node_name_2 = "node2"
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                [
                    *_create_interfaces(0, node=node_name_1),
                    *_create_interfaces(0, node=node_name_2),
                ],
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            [
                *_create_interfaces(4000000, node=node_name_1),
                *_create_interfaces(4000000, node=node_name_2),
            ],
            timestamp=5,
        )
    ) == _add_node_name_to_results(result, node_name_1)


def test_check_multiple_interfaces_group_multiple_nodes() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("upper", ("perc", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("upper", ("perc", (10.0, 30.0))),
            ]
        },
        "aggregate": {
            "member_appearance": "index",
            "inclusion_condition": {"match_index": ["5", "6"]},
            "exclusion_conditions": [
                {
                    "admin_states": ["3"],
                },
            ],
        },
        "discovered_oper_status": ["1"],
        "discovered_speed": 20000000,
    }
    node_names = ["node1", "node2", "node3"]
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.check_multiple_interfaces(
                "group",
                params,
                sum(
                    (
                        _create_interfaces(
                            0,
                            admin_status=str(idx + 1),
                            node=node_name,
                        )
                        for idx, node_name in enumerate(node_names)
                    ),
                    [],
                ),
                timestamp=0,
            )
        )
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            sum(
                (
                    _create_interfaces(
                        4000000,
                        admin_status=str(idx + 1),
                        node=node_name,
                    )
                    for idx, node_name in enumerate(node_names)
                ),
                [],
            ),
            timestamp=5,
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(
            state=State.OK,
            summary="Members: [5 (op. state: up, admin state: up), 6 (op. state: up, admin state: up) on node node1] [5 (op. state: up, admin state: down), 6 (op. state: up, admin state: down) on node node2]",
        ),
        Result(state=State.OK, summary="Speed: 20 MBit/s"),
        Metric("outqlen", 0.0),
        Result(state=State.CRIT, summary="In: 1.60 MB/s (warn/crit at 125 kB/s/500 kB/s) (64.00%)"),
        Metric("in", 1600000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Out: 6.40 MB/s (warn/crit at 125 kB/s/500 kB/s) (256.00%)"
        ),
        Metric("out", 6400000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(
            state=State.CRIT, summary="Total: 8.00 MB/s (warn/crit at 500 kB/s/1.50 MB/s) (160.00%)"
        ),
        Metric("total", 8000000.0, levels=(500000.0, 1500000.0), boundaries=(0.0, 5000000.0)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]


def test_cluster_check(monkeypatch: MonkeyPatch) -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "speed": 10000000,
        "traffic": [
            ("both", ("upper", ("perc", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("upper", ("perc", (10.0, 30.0))),
            ]
        },
        "state": ["1"],
    }
    section = {}
    ifaces = []
    for i in range(3):
        iface = _create_interfaces(0)[0]
        iface.node = "node%s" % i
        ifaces_node = [iface] * (i + 1)
        section[iface.node] = ifaces_node
        ifaces += ifaces_node
    monkeypatch.setattr("time.time", lambda: 0)
    with pytest.raises(IgnoreResultsError):
        list(
            interfaces.cluster_check(
                "1",
                params,
                section,
            )
        )
    monkeypatch.setattr("time.time", lambda: 1)
    result_cluster_check = list(
        interfaces.cluster_check(
            "1",
            params,
            section,
        )
    )
    monkeypatch.setattr("time.time", lambda: 2)
    result_check_multiple_interfaces = list(
        interfaces.check_multiple_interfaces(
            "1",
            params,
            ifaces,
        )
    )
    assert result_cluster_check == result_check_multiple_interfaces


def test_cluster_check_ignore_discovered_params() -> None:
    assert list(
        interfaces.cluster_check(
            "1",
            {
                "discovered_oper_status": ["2"],
                "discovered_speed": 200000,
            },
            {
                "node": [
                    interfaces.Interface(
                        index="1",
                        descr="descr",
                        alias="alias",
                        type="10",
                        speed=100000,
                        oper_status="1",
                    ),
                ],
            },
        )
    ) == [
        Result(
            state=State.OK,
            summary="[alias] on node",
        ),
        # TODO: Fix the following two results
        Result(
            state=State.OK,
            summary="(up)",
            details="Operational state: up",
        ),
        Result(
            state=State.OK,
            summary="Speed: 100 kBit/s",
        ),
    ]
