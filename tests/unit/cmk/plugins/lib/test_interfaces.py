#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.v2 import IgnoreResults, Metric, Result, Service, ServiceLabel, State
from cmk.plugins.lib import interfaces

CheckResults = Sequence[Result | Metric | IgnoreResults]


def _create_interfaces_with_counters(
    bandwidth_change: int,
    **attr_kwargs: Any,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    ifaces = [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="1",
                descr="lo",
                alias="lo",
                type="24",
                speed=0,
                oper_status="1",
                phys_address="\x00\x00\x00\x00\x00\x00",
            ),
            interfaces.Counters(
                in_octets=266045395,
                in_ucast=97385,
                out_octets=266045395,
                out_ucast=97385,
            ),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="docker0",
                alias="docker0",
                type="6",
                speed=0,
                oper_status="2",
                phys_address="\x02B\x9d\xa42/",
            ),
            interfaces.Counters(),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="3",
                descr="enp0s31f6",
                alias="enp0s31f6",
                type="6",
                speed=0,
                oper_status="2",
                phys_address="\xe4\xb9z6\x93\xad",
            ),
            interfaces.Counters(),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="4",
                descr="enxe4b97ab99f99",
                alias="enxe4b97ab99f99",
                type="6",
                speed=10000000,
                oper_status="2",
                phys_address="\xe4\xb9z\xb9\x9f\x99",
            ),
            interfaces.Counters(),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="5",
                descr="vboxnet0",
                alias="vboxnet0",
                type="6",
                speed=10000000,
                oper_status="1",
                out_qlen=32.2,
                phys_address="\n\x00'\x00\x00\x00",
            ),
            interfaces.Counters(
                out_octets=20171,
                out_ucast=113,
            ),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="6",
                descr="wlp2s0",
                alias="wlp2s0",
                type="6",
                speed=0,
                oper_status="1",
                out_qlen=0,
                phys_address="d]\x86\xe4P/",
            ),
            interfaces.Counters(
                in_octets=346922243 + bandwidth_change,
                in_ucast=244867,
                in_bcast=0,
                in_mcast=0,
                in_err=0,
                in_disc=0,
                out_octets=6570143 + 4 * bandwidth_change,
                out_ucast=55994,
                out_bcast=0,
                out_mcast=0,
                out_err=0,
                out_disc=0,
            ),
        ),
    ]
    for iface in ifaces:
        for k, v in attr_kwargs.items():
            setattr(iface.attributes, k, v)
    return ifaces


def _create_interfaces_with_rates(
    *,
    bandwidth_change: int = 0,
    timedelta: int = 0,
    params: Mapping[str, Any] | None = None,
    **attr_kwargs: Any,
) -> Sequence[interfaces.InterfaceWithRatesAndAverages]:
    value_store: dict[str, Any] = {}
    _init = [
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            iface,
            timestamp=0,
            value_store=value_store,
            params=params or {},
        )
        for iface in _create_interfaces_with_counters(0, **attr_kwargs)
    ]
    return [
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            iface,
            timestamp=timedelta,
            value_store=value_store,
            params=params or {},
        )
        for iface in _create_interfaces_with_counters(bandwidth_change, **attr_kwargs)
    ]


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
        parameters={
            "item_appearance": "index",
            "discovered_oper_status": ["1"],
            "discovered_speed": 10000000,
        },
    ),
    Service(
        item="6",
        parameters={
            "item_appearance": "index",
            "discovered_oper_status": ["1"],
            "discovered_speed": 0,
        },
    ),
]


def test_discovery_ungrouped_all() -> None:
    assert (
        list(
            interfaces.discover_interfaces(
                [DEFAULT_DISCOVERY_PARAMS],
                _create_interfaces_with_counters(0),
            )
        )
        == SINGLE_SERVICES
    )


def test_discovery_ungrouped_empty_section() -> None:
    assert not list(
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


def test_discovery_ungrouped_admin_status() -> None:
    ifaces = _create_interfaces_with_counters(0, admin_status="1")
    ifaces[-1].attributes.admin_status = "2"
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
                "item_appearance": "index",
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
                _create_interfaces_with_counters(0),
            )
        )
        == SINGLE_SERVICES[1:]
    )


def test_discovery_ungrouped_off() -> None:
    assert not list(
        interfaces.discover_interfaces(
            [
                {
                    "matching_conditions": (True, {}),
                    "discovery_single": (False, {}),
                },
                DEFAULT_DISCOVERY_PARAMS,
            ],
            _create_interfaces_with_counters(0),
        )
    )


def test_discovery_duplicate_index() -> None:
    assert list(
        interfaces.discover_interfaces(
            [DEFAULT_DISCOVERY_PARAMS],
            _create_interfaces_with_counters(0, index="1"),
        )
    ) == [
        Service(
            item="1",
            parameters={
                "item_appearance": "index",
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
            _create_interfaces_with_counters(0, descr="description"),
        )
    ) == [
        Service(
            item="description 5",
            parameters={
                "item_appearance": "descr",
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="description 6",
            parameters={
                "item_appearance": "descr",
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
            _create_interfaces_with_counters(0, alias="alias"),
        )
    ) == [
        Service(
            item="alias 5",
            parameters={
                "item_appearance": "alias",
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
    ]


def test_discovery_partial_duplicate_desc_duplicate_alias() -> None:
    ifaces = _create_interfaces_with_counters(0)
    ifaces[3].attributes.descr = "duplicate_descr"
    ifaces[4].attributes.descr = "duplicate_descr"
    for iface in ifaces:
        iface.attributes.alias = "alias"
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
                "item_appearance": "descr",
                "discovered_oper_status": ["2"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="duplicate_descr 5",
            parameters={
                "item_appearance": "descr",
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=[],
        ),
        Service(
            item="wlp2s0",
            parameters={
                "item_appearance": "descr",
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
            _create_interfaces_with_counters(0),
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
            _create_interfaces_with_counters(0),
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
            _create_interfaces_with_counters(0),
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
                _create_interfaces_with_counters(0),
            )
        )
        == SINGLE_SERVICES
    )


def test_discovery_grouped_by_agent() -> None:
    ifaces = _create_interfaces_with_counters(0)
    ifaces[0].attributes.group = "group"
    ifaces[1].attributes.group = "group"
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
    ifaces = _create_interfaces_with_counters(0)
    ifaces[0].attributes.group = "group"
    ifaces[1].attributes.group = "group"
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
            _create_interfaces_with_counters(0),
        )
    ) == [
        Service(
            item="lo",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="docker0",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="enp0s31f6",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="enxe4b97ab99f99",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 10000000,
                "item_appearance": "alias",
            },
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="vboxnet0",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
                "item_appearance": "alias",
            },
            labels=[ServiceLabel("single", "default")],
        ),
        Service(
            item="wlp2s0",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
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
                ("both", ("perc", ("upper", (5.0, 20.0)))),
            ],
            "state": ["1"],
        },
        [
            Result(state=State.OK, summary="[vboxnet0]"),
            Result(state=State.OK, summary="(up)", details="Operational state: up"),
            Result(state=State.OK, summary="MAC: 0A:00:27:00:00:00"),
            Result(state=State.OK, summary="Speed: 10 MBit/s"),
            Metric("outqlen", 32.2),
            Result(state=State.OK, summary="Out: 0.00 B/s (0%)"),
            Metric("out", 0.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
        ],
    ),
    (
        "6",
        {
            "errors": {"both": ("abs", (10, 20))},
            "speed": 100_000_000,
            "traffic": [
                ("both", ("perc", ("upper", (5.0, 20.0)))),
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
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0),
            Result(state=State.OK, notice="Multicast in: 0 packets/s"),
            Metric("inmcast", 0.0),
            Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
            Metric("inbcast", 0.0),
            Result(state=State.OK, notice="Unicast in: 0 packets/s"),
            Metric("inucast", 0.0),
            Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
            Metric("innucast", 0.0),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0),
            Result(state=State.OK, notice="Multicast out: 0 packets/s"),
            Metric("outmcast", 0.0),
            Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
            Metric("outbcast", 0.0),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
            Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
            Metric("outnucast", 0.0),
        ],
    ),
    (
        "6",
        {
            "errors": {"both": ("abs", (10, 20))},
            "speed": 100000000,
            "traffic": [("both", ("perc", ("upper", (5.0, 20.0))))],
            "state": ["1"],
            "nucasts": (1, 2),
            "discards": {"both": ("abs", (1, 2))},
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
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Multicast in: 0 packets/s"),
            Metric("inmcast", 0.0),
            Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
            Metric("inbcast", 0.0),
            Result(state=State.OK, notice="Unicast in: 0 packets/s"),
            Metric("inucast", 0.0),
            Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
            Metric("innucast", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0, levels=(10.0, 20.0)),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0, levels=(1.0, 2.0)),
            Result(state=State.OK, notice="Multicast out: 0 packets/s"),
            Metric("outmcast", 0.0),
            Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
            Metric("outbcast", 0.0),
            Result(state=State.OK, notice="Unicast out: 0 packets/s"),
            Metric("outucast", 0.0),
            Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
            Metric("outnucast", 0.0, levels=(1.0, 2.0)),
        ],
    ),
)


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    assert (
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces_with_rates(
                    bandwidth_change=4000000,
                    timedelta=5,
                    params=params,
                )[int(item) - 1],
            )
        )
        == result
    )


def test_check_single_interface_same_index_descr_alias() -> None:
    item = "07"
    result = next(
        iter(
            interfaces.check_single_interface(
                item,
                {},
                _create_interfaces_with_rates(
                    index=item,
                    descr=item,
                    alias=item,
                )[0],
            )
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
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="1",
            )[int(item) - 1],
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
    assert list(
        interfaces.check_single_interface(
            item,
            {
                **params,
                "state": ["4"],
                "admin_state": ["2"],
            },
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="1",
            )[int(item) - 1],
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
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="2",
            )[int(item) - 1],
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
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="2",
            )[int(item) - 1],
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
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="3",
            )[int(item) - 1],
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
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                admin_status="3",
            )[int(item) - 1],
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
    assert (
        list(
            interfaces.check_single_interface(
                item,
                {
                    **params,
                    "state": None,
                },
                _create_interfaces_with_rates(
                    bandwidth_change=4000000,
                    timedelta=5,
                    params=params,
                    oper_status=4,
                )[int(item) - 1],
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
                Result(state=State.OK, summary="Out average 5min: 0.00 B/s (0%)"),
            ]
            + ITEM_PARAMS_RESULTS[0][2][6:],
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
def test_check_single_interface_bandwidth_averaging(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    params = {
        **params,
        "average": 5,
    }
    assert (
        list(
            interfaces.check_single_interface(
                item,
                params,
                _create_interfaces_with_rates(
                    bandwidth_change=4000000,
                    timedelta=5,
                    params=params,
                )[int(item) - 1],
            )
        )
        == result
    )


def test_check_single_interface_bm_averaging() -> None:
    item = "6"
    params = {"average_bm": 13}
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
            )[int(item) - 1],
        )
    ) == [
        Result(state=State.OK, summary="[wlp2s0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="MAC: 64:5D:86:E4:50:2F"),
        Result(state=State.OK, summary="Speed: unknown"),
        Metric("outqlen", 0.0),
        Result(state=State.OK, summary="In: 800 kB/s"),
        Metric("in", 800000.0, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 3.20 MB/s"),
        Metric("out", 3200000.0, boundaries=(0.0, None)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Multicast in average 13min: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in average 13min: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
        Result(state=State.OK, notice="Multicast out average 13min: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out average 13min: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    group_members: interfaces.GroupMembers = {
        None: [
            interfaces.MemberInfo(name="vboxnet0", oper_status_name="up"),
            interfaces.MemberInfo(name="wlp2s0", oper_status_name="up"),
        ]
    }
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
            )[int(item) - 1],
            group_members=group_members,
        )
    ) == _add_group_info_to_results(result, "Members: [vboxnet0 (up), wlp2s0 (up)]")


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group_admin_status(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    group_members: interfaces.GroupMembers = {
        None: [
            interfaces.MemberInfo(name="vboxnet0", oper_status_name="up", admin_status_name="down"),
            interfaces.MemberInfo(
                name="wlp2s0", oper_status_name="up", admin_status_name="testing"
            ),
        ]
    }
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
            )[int(item) - 1],
            group_members=group_members,
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
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
                node=node_name,
            )[int(item) - 1],
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
            interfaces.MemberInfo(name="vboxnet0", oper_status_name="up"),
            interfaces.MemberInfo(name="wlp2s0", oper_status_name="up"),
        ],
        "node2": [
            interfaces.MemberInfo(name="vboxnet0", oper_status_name="up"),
            interfaces.MemberInfo(name="wlp2s0", oper_status_name="up"),
        ],
    }
    assert list(
        interfaces.check_single_interface(
            item,
            params,
            _create_interfaces_with_rates(
                bandwidth_change=4000000,
                timedelta=5,
                params=params,
            )[int(item) - 1],
            group_members=group_members,
        )
    ) == _add_group_info_to_results(
        result,
        "Members: [vboxnet0 (up), wlp2s0 (up) on node node1] [vboxnet0 (up), wlp2s0 (up) on node "
        "node2]",
    )


def test_check_single_interface_packet_levels() -> None:
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
                "discards": {
                    "both": ("abs", (50.0, 300.0)),
                },
            },
            interfaces.InterfaceWithRatesAndAverages(
                interfaces.Attributes(
                    index="1",
                    descr="lo",
                    alias="lo",
                    type="24",
                    speed=0,
                    oper_status="1",
                    phys_address="\x00\x00\x00\x00\x00\x00",
                ),
                interfaces.RatesWithAverages(
                    in_octets=interfaces.RateWithAverage(266045395, None),
                    in_ucast=interfaces.RateWithAverage(10, None),
                    in_mcast=interfaces.RateWithAverage(20, None),
                    in_bcast=interfaces.RateWithAverage(30, None),
                    in_nucast=interfaces.RateWithAverage(50, None),
                    in_disc=interfaces.RateWithAverage(40, None),
                    in_err=interfaces.RateWithAverage(50, None),
                    out_octets=interfaces.RateWithAverage(266045395, None),
                    out_ucast=interfaces.RateWithAverage(60, None),
                    out_mcast=interfaces.RateWithAverage(70, None),
                    out_bcast=interfaces.RateWithAverage(80, None),
                    out_nucast=interfaces.RateWithAverage(150, None),
                    out_disc=interfaces.RateWithAverage(90, None),
                    out_err=interfaces.RateWithAverage(100, None),
                    total_octets=interfaces.RateWithAverage(532090790, None),
                ),
                get_rate_errors=[],
            ),
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
            state=State.OK,
            notice="Discards in: 40 packets/s",
        ),
        Metric(
            "indisc",
            40.0,
            levels=(50.0, 300.0),
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
            state=State.CRIT,
            summary="Errors out: 100 packets/s (warn/crit at 10 packets/s/20 packets/s)",
        ),
        Metric(
            "outerr",
            100.0,
            levels=(10.0, 20.0),
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
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    ifaces = _create_interfaces_with_counters(0)
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000)
    assert (
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                ifaces,
                timestamps=[5] * len(ifaces),
            )
        )
        == result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_descr(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    description = "description"
    item = f"{description} {item}"
    ifaces = _create_interfaces_with_counters(0, descr=description)
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, descr=description)
    assert (
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                ifaces,
                timestamps=[5] * len(ifaces),
            )
        )
        == result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_alias(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    alias = "alias"
    index = item
    item = f"{alias} {index}"
    ifaces = _create_interfaces_with_counters(0, alias=alias)
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, alias=alias)
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == [
        Result(
            state=State.OK,
            summary=f"[{alias}/{ifaces[int(index) - 1].attributes.descr}]",
        ),
        *result[1:],
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_multiple_interfaces_group_simple() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("perc", ("upper", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("perc", ("upper", (10.0, 30.0))),
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
    ifaces = _create_interfaces_with_counters(0)
    list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000)
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.OK, summary="(degraded)", details="Operational state: degraded"),
        Result(
            state=State.OK,
            summary="Members: [1 (up), 2 (down), 3 (down), 4 (down), 5 (up), 6 (up)]",
        ),
        Result(state=State.WARN, summary="Speed: 10 MBit/s (expected: 123 kBit/s)"),
        Result(
            state=State.CRIT, summary="Out: 3.20 MB/s (warn/crit at 62.5 kB/s/250 kB/s) (256.00%)"
        ),
        Metric("out", 3200000.0, levels=(62500.0, 250000.0), boundaries=(0.0, 1250000.0)),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_multiple_interfaces_group_exclude() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("perc", ("upper", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("perc", ("upper", (10.0, 30.0))),
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

    ifaces = _create_interfaces_with_counters(0)
    list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000)
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.CRIT, summary="(degraded)", details="Operational state: degraded"),
        Result(state=State.OK, summary="Members: [1 (up), 2 (down), 3 (down), 6 (up)]"),
        Result(state=State.OK, summary="Speed: 20 MBit/s (assumed)"),
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
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_multiple_interfaces_group_by_agent() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("perc", ("upper", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("perc", ("upper", (10.0, 30.0))),
            ]
        },
        "aggregate": {
            "member_appearance": "index",
        },
        "discovered_oper_status": ["1"],
        "discovered_speed": 20000000,
    }

    ifaces = _create_interfaces_with_counters(0)
    ifaces[3].attributes.group = "group"
    ifaces[5].attributes.group = "group"
    list(
        interfaces.check_multiple_interfaces("group", params, ifaces, timestamps=[0] * len(ifaces))
    )

    ifaces = _create_interfaces_with_counters(4000000)
    ifaces[3].attributes.group = "group"
    ifaces[5].attributes.group = "group"
    assert list(
        interfaces.check_multiple_interfaces("group", params, ifaces, timestamps=[5] * len(ifaces))
    ) == [
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
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0, levels=(10.0, 20.0)),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_w_node(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    node_name = "node"
    ifaces = _create_interfaces_with_counters(0, node=node_name)
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, node=node_name)
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == _add_node_name_to_results(result, node_name)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_same_item_twice_cluster(
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    node_name_1 = "node1"
    node_name_2 = "node2"
    ifaces = [
        *_create_interfaces_with_counters(0, node=node_name_1),
        *_create_interfaces_with_counters(0, node=node_name_2),
    ]
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = [
        *_create_interfaces_with_counters(4000000, node=node_name_1),
        *_create_interfaces_with_counters(4000000, node=node_name_2),
    ]
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == _add_node_name_to_results(result, node_name_1)


@pytest.mark.usefixtures("initialised_item_state")
def test_check_multiple_interfaces_group_multiple_nodes() -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "traffic": [
            ("both", ("perc", ("upper", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("perc", ("upper", (10.0, 30.0))),
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
    ifaces = [
        interface
        for idx, node_name in enumerate(node_names)
        for interface in _create_interfaces_with_counters(
            0,
            admin_status=str(idx + 1),
            node=node_name,
        )
    ]
    list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[0] * len(ifaces),
        )
    )
    ifaces = [
        interface
        for idx, node_name in enumerate(node_names)
        for interface in _create_interfaces_with_counters(
            4000000,
            admin_status=str(idx + 1),
            node=node_name,
        )
    ]
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
            timestamps=[5] * len(ifaces),
        )
    ) == [
        Result(state=State.OK, summary="Interface group"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(
            state=State.OK,
            summary="Members: [5 (op. state: up, admin state: up), 6 (op. state: up, admin state: up) on node node1] [5 (op. state: up, admin state: down), 6 (op. state: up, admin state: down) on node node2]",
        ),
        Result(state=State.OK, summary="Speed: 20 MBit/s"),
        Metric("outqlen", 64.4),
        Result(
            state=State.CRIT, summary="Out: 6.40 MB/s (warn/crit at 125 kB/s/500 kB/s) (256.00%)"
        ),
        Metric("out", 6400000.0, levels=(125000.0, 500000.0), boundaries=(0.0, 2500000.0)),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
def test_cluster_check(monkeypatch: MonkeyPatch) -> None:
    params = {
        "errors": {"both": ("abs", (10, 20))},
        "speed": 10000000,
        "traffic": [
            ("both", ("perc", ("upper", (5.0, 20.0)))),
        ],
        "total_traffic": {
            "levels": [
                ("perc", ("upper", (10.0, 30.0))),
            ]
        },
        "state": ["1"],
    }
    section = {}
    ifaces = []
    for i in range(3):
        iface = _create_interfaces_with_counters(0)[0]
        iface.attributes.node = "node%s" % i
        ifaces_node = [iface] * (i + 1)
        section[iface.attributes.node] = ifaces_node
        ifaces += ifaces_node
    monkeypatch.setattr("time.time", lambda: 0)
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


@pytest.mark.usefixtures("initialised_item_state")
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
                    interfaces.InterfaceWithCounters(
                        interfaces.Attributes(
                            index="1",
                            descr="descr",
                            alias="alias",
                            type="10",
                            speed=100000,
                            oper_status="1",
                        ),
                        interfaces.Counters(),
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


@pytest.mark.parametrize(
    ["item", "section", "expected_matches"],
    [
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="Port 1",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port 2",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="Port 2",
                    alias="",
                    type="10",
                )
            ],
            id="unclustered, simple item",
        ),
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="Port",
                    type="10",
                )
            ],
            id="unclustered, compound item",
        ),
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port 2",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="1",
                    descr="",
                    alias="Port 2",
                    type="10",
                )
            ],
            id="unclustered, simple and compound mixed",
        ),
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="Port 1",
                        alias="",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port 2",
                        alias="",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="10",
                        descr="Port 2",
                        alias="",
                        type="10",
                        node="node2",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="Port 2",
                    alias="",
                    type="10",
                    node="node1",
                ),
                interfaces.Attributes(
                    index="10",
                    descr="Port 2",
                    alias="",
                    type="10",
                    node="node2",
                ),
            ],
            id="clustered, simple item",
        ),
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node2",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="Port",
                    type="10",
                    node="node1",
                ),
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="Port",
                    type="10",
                    node="node2",
                ),
            ],
            id="clustered, compound item",
        ),
        pytest.param(
            "Port 2",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port 2",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port",
                        alias="",
                        type="10",
                        node="node2",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="1",
                    descr="",
                    alias="Port 2",
                    type="10",
                    node="node1",
                ),
                interfaces.Attributes(
                    index="2",
                    descr="Port",
                    alias="",
                    type="10",
                    node="node2",
                ),
            ],
            id="clustered, simple and compound mixed",
        ),
    ],
)
def test_matching_interfaces_for_item(
    item: str,
    section: interfaces.Section[interfaces.TInterfaceType],
    expected_matches: Sequence[interfaces.Attributes],
) -> None:
    assert [
        iface.attributes
        for iface in interfaces.matching_interfaces_for_item(
            item,
            section,
        )
    ] == expected_matches


@pytest.mark.parametrize(
    ["item", "appearance", "section", "expected_matches"],
    [
        pytest.param(
            "1",
            None,
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port 1",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="1",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="1",
                    descr="",
                    alias="Port 1",
                    type="10",
                )
            ],
            id="Support legacy matching logic simple",
        ),
        pytest.param(
            "1",
            "alias",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port 1",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="1",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="1",
                    type="10",
                )
            ],
            id="Clear up index alias mixup simple",
        ),
        pytest.param(
            "1",
            "descr",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="Port 1",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="1",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="1",
                    alias="",
                    type="10",
                )
            ],
            id="Clear up index descr mixup simple",
        ),
        pytest.param(
            "Port 2",
            None,
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port 2",
                        alias="",
                        type="10",
                        node="node2",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="Port",
                    type="10",
                    node="node1",
                ),
                interfaces.Attributes(
                    index="2",
                    descr="Port 2",
                    alias="",
                    type="10",
                    node="node2",
                ),
            ],
            id="Support legacy matching logic compound, descr mixup is picked up",
        ),
        pytest.param(
            "Port 2",
            "alias",
            [
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="1",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                        node="node1",
                    ),
                    interfaces.Counters(),
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port 2",
                        alias="",
                        type="10",
                        node="node2",
                    ),
                    interfaces.Counters(),
                ),
            ],
            [
                interfaces.Attributes(
                    index="2",
                    descr="",
                    alias="Port",
                    type="10",
                    node="node1",
                ),
            ],
            id="Clear up descr mixup compound",
        ),
    ],
)
def test_matching_interfaces_for_item_clear_mixup_with_appearance(
    item: str,
    appearance: interfaces._ItemAppearance | None,
    section: interfaces.Section[interfaces.TInterfaceType],
    expected_matches: Sequence[interfaces.Attributes],
) -> None:
    assert [
        iface.attributes
        for iface in interfaces.matching_interfaces_for_item(
            item,
            section,
            appearance,
        )
    ] == expected_matches


def test_non_unicast_packets_handling() -> None:
    iface_with_counters = interfaces.InterfaceWithCounters(
        interfaces.Attributes(
            index="1",
            descr="lo",
            alias="lo",
            type="24",
            speed=0,
            oper_status="1",
            phys_address="\x00\x00\x00\x00\x00\x00",
        ),
        interfaces.Counters(
            in_nucast=0,
            out_nucast=0,
        ),
    )
    value_store: dict[str, object] = {}

    # first call: value store initalization
    interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
        iface_with_counters,
        timestamp=0,
        value_store=value_store,
        params={},
    )
    # second call: rate computation
    iface_with_rates_and_averages = (
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            iface_with_counters,
            timestamp=1,
            value_store=value_store,
            params={},
        )
    )

    assert list(interfaces.check_single_interface("1", {}, iface_with_rates_and_averages)) == [
        Result(state=State.OK, summary="[lo]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="MAC: 00:00:00:00:00:00"),
        Result(state=State.OK, summary="Speed: unknown"),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]
