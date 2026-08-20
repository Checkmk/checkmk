#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.v2 import IgnoreResults, Metric, Result, Service, ServiceLabel, State
from cmk.plugins.lib import interfaces

CheckResults = Sequence[Result | Metric | IgnoreResults]


@pytest.fixture
def initialised_item_state(monkeypatch: MonkeyPatch) -> None:
    value_store: dict[str, Any] = {}
    monkeypatch.setattr(interfaces, "get_value_store", lambda: value_store)


def _create_interfaces_with_counters(
    bandwidth_change: int,
    timestamp: float = 0.0,
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
            timestamp,
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
            timestamp,
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
            timestamp,
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
            timestamp,
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
            timestamp,
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
                in_nucast=0,
                in_bcast=0,
                in_mcast=0,
                in_err=0,
                in_disc=0,
                out_octets=6570143 + 4 * bandwidth_change,
                out_ucast=55994,
                out_nucast=0,
                out_bcast=0,
                out_mcast=0,
                out_err=0,
                out_disc=0,
            ),
            timestamp,
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
            value_store=value_store,
            params=params or {},
        )
        for iface in _create_interfaces_with_counters(0, 0.0, **attr_kwargs)
    ]
    return [
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            iface,
            value_store=value_store,
            params=params or {},
        )
        for iface in _create_interfaces_with_counters(bandwidth_change, timedelta, **attr_kwargs)
    ]


def _add_node_name_to_results(
    results: CheckResults,
    node_name: str,
) -> CheckResults:
    res = results[0]
    assert isinstance(res, Result)
    # mirrors _interface_name: the node is appended to the summary, but appears as its own
    # line in the interface identification block which makes up the details
    return [
        Result(
            state=res.state,
            summary=f"{res.summary} on {node_name}" if res.summary else f"On {node_name}",
            details=f"{res.details}\nNode: {node_name}",
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


def _network_interface_labels(index: str, descr: str, alias: str) -> list[ServiceLabel]:
    """Build the automatic ``cmk/network_interface/*`` labels emitted by discovery.

    Mirrors ``discover_interfaces``: the index label is always present, the description and
    alias labels are only emitted for non-empty values.
    """
    labels = [ServiceLabel("cmk/network_interface/index", index)]
    if descr:
        labels.append(ServiceLabel("cmk/network_interface/description", descr))
    if alias:
        labels.append(ServiceLabel("cmk/network_interface/alias", alias))
    return labels


SINGLE_SERVICES = [
    Service(
        item="5",
        parameters={
            "item_appearance": "index",
            "discovered_oper_status": ["1"],
            "discovered_speed": 10000000,
        },
        labels=_network_interface_labels("5", "vboxnet0", "vboxnet0"),
    ),
    Service(
        item="6",
        parameters={
            "item_appearance": "index",
            "discovered_oper_status": ["1"],
            "discovered_speed": 0,
        },
        labels=_network_interface_labels("6", "wlp2s0", "wlp2s0"),
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
            labels=_network_interface_labels("5", "vboxnet0", "vboxnet0"),
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
            labels=_network_interface_labels("1", "vboxnet0", "vboxnet0"),
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
            labels=_network_interface_labels("5", "description", "vboxnet0"),
        ),
        Service(
            item="description 6",
            parameters={
                "item_appearance": "descr",
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
            },
            labels=_network_interface_labels("6", "description", "wlp2s0"),
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
            labels=_network_interface_labels("5", "vboxnet0", "alias"),
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
            labels=_network_interface_labels("4", "duplicate_descr", "alias"),
        ),
        Service(
            item="duplicate_descr 5",
            parameters={
                "item_appearance": "descr",
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
            },
            labels=_network_interface_labels("5", "duplicate_descr", "alias"),
        ),
        Service(
            item="wlp2s0",
            parameters={
                "item_appearance": "descr",
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
            },
            labels=_network_interface_labels("6", "wlp2s0", "alias"),
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
            labels=[ServiceLabel("single", "default"), *_network_interface_labels("1", "lo", "lo")],
        ),
        Service(
            item="docker0",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[
                ServiceLabel("single", "default"),
                *_network_interface_labels("2", "docker0", "docker0"),
            ],
        ),
        Service(
            item="enp0s31f6",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[
                ServiceLabel("single", "default"),
                *_network_interface_labels("3", "enp0s31f6", "enp0s31f6"),
            ],
        ),
        Service(
            item="enxe4b97ab99f99",
            parameters={
                "discovered_oper_status": ["2"],
                "discovered_speed": 10000000,
                "item_appearance": "alias",
            },
            labels=[
                ServiceLabel("single", "default"),
                *_network_interface_labels("4", "enxe4b97ab99f99", "enxe4b97ab99f99"),
            ],
        ),
        Service(
            item="vboxnet0",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 10000000,
                "item_appearance": "alias",
            },
            labels=[
                ServiceLabel("single", "default"),
                *_network_interface_labels("5", "vboxnet0", "vboxnet0"),
            ],
        ),
        Service(
            item="wlp2s0",
            parameters={
                "discovered_oper_status": ["1"],
                "discovered_speed": 0,
                "item_appearance": "alias",
            },
            labels=[
                ServiceLabel("single", "wlp"),
                *_network_interface_labels("6", "wlp2s0", "wlp2s0"),
            ],
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
            Result(
                state=State.OK,
                summary="[vboxnet0]",
                details="Index: 5\nDescription: vboxnet0\nAlias: vboxnet0",
            ),
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
            Result(
                state=State.OK,
                summary="[wlp2s0]",
                details="Index: 6\nDescription: wlp2s0\nAlias: wlp2s0",
            ),
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
            Result(state=State.OK, notice="Non-Unicast in: 0 packets/s"),
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
            Result(state=State.OK, notice="Non-Unicast out: 0 packets/s"),
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
            "nucasts": {"both": ("abs", (1, 2))},
            "discards": {"both": ("abs", (1, 2))},
        },
        [
            Result(
                state=State.OK,
                summary="[wlp2s0]",
                details="Index: 6\nDescription: wlp2s0\nAlias: wlp2s0",
            ),
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
            Result(state=State.OK, notice="Non-Unicast in: 0 packets/s"),
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
            Result(state=State.OK, notice="Non-Unicast out: 0 packets/s"),
            Metric("outnucast", 0.0, levels=(1.0, 2.0)),
        ],
    ),
)


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface(  # type: ignore[misc]
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
    results = list(
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
    # the interface identification does not contribute to the summary here, since index,
    # description and alias are all identical to the item
    assert results[:2] == [
        Result(
            state=State.OK,
            notice="Index: 07\nDescription: 07\nAlias: 07",
        ),
        Result(
            state=State.OK,
            summary="(up)",
            details="Operational state: up",
        ),
    ]
    assert results[0].summary == ""  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ["item", "params", "attributes", "expected"],
    [
        pytest.param(
            "eth0",
            {"item_appearance": "descr"},
            interfaces.Attributes(index="3", descr="eth0", alias="uplink to core", type="6"),
            [
                Result(
                    state=State.OK,
                    summary="[uplink to core]",
                    details="Index: 3\n"
                    "Description: eth0\n"
                    "Alias: uplink to core\n"
                    "Service item based on: description (ifDescr)",
                ),
            ],
            id="item is the description",
        ),
        pytest.param(
            "uplink to core",
            {"item_appearance": "alias"},
            interfaces.Attributes(index="3", descr="eth0", alias="uplink to core", type="6"),
            [
                Result(
                    state=State.OK,
                    summary="[eth0]",
                    details="Index: 3\n"
                    "Description: eth0\n"
                    "Alias: uplink to core\n"
                    "Service item based on: alias (ifAlias)",
                ),
            ],
            id="item is the alias",
        ),
        pytest.param(
            "3",
            {"item_appearance": "index"},
            interfaces.Attributes(index="3", descr="", alias="", type="6"),
            [
                Result(
                    state=State.OK,
                    notice="Index: 3\n"
                    "Description: not set\n"
                    "Alias: not set\n"
                    "Service item based on: index (ifIndex)",
                ),
            ],
            id="device populates neither description nor alias",
        ),
        pytest.param(
            "Ethernet1",
            {"item_appearance": "name"},
            interfaces.Attributes(
                index="3", descr="eth0", alias="uplink", name="Ethernet1", type="6"
            ),
            [
                Result(
                    state=State.OK,
                    summary="[uplink]",
                    details="Index: 3\n"
                    "Description: eth0\n"
                    "Alias: uplink\n"
                    "Name: Ethernet1\n"
                    "Service item based on: name (ifName)",
                ),
            ],
            id="item is the name",
        ),
        pytest.param(
            "eth0",
            {},
            interfaces.Attributes(index="3", descr="eth0", alias="uplink", type="6"),
            [
                Result(
                    state=State.OK,
                    summary="[uplink]",
                    details="Index: 3\nDescription: eth0\nAlias: uplink",
                ),
            ],
            id="no discovered item appearance available",
        ),
    ],
)
def test_interface_name_identification(
    item: str,
    params: Mapping[str, object],
    attributes: interfaces.Attributes,
    expected: CheckResults,
) -> None:
    assert (
        list(
            interfaces._interface_name(  # noqa: SLF001
                group_name=None,
                item=item,
                params=params,
                attributes=attributes,
            )
        )
        == expected
    )


def test_interface_name_identification_omitted_for_groups() -> None:
    # for groups, index/descr/alias of the accumulated attributes carry no device
    # information, so no identification block must be rendered
    assert list(
        interfaces._interface_name(  # noqa: SLF001
            group_name="Interface group",
            item="my-group",
            params={},
            attributes=interfaces.Attributes(
                index="my-group",
                descr="my-group",
                alias="type: 6, 2 grouped interfaces",
                type="6",
            ),
        )
    ) == [Result(state=State.OK, summary="Interface group")]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_admin_status(  # type: ignore[misc]
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
def test_check_single_interface_states(  # type: ignore[misc]
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
def test_check_single_interface_map_states_independently(  # type: ignore[misc]
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
def test_check_single_interface_map_states_combined_matching(  # type: ignore[misc]
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
def test_check_single_interface_map_states_combined_not_matching(  # type: ignore[misc]
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
def test_check_single_interface_map_states_combined_not_matching_with_target_states(  # type: ignore[misc]
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
def test_check_single_interface_ignore_state(  # type: ignore[misc]
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
def test_check_single_interface_bandwidth_averaging(  # type: ignore[misc]
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
        Result(
            state=State.OK,
            summary="[wlp2s0]",
            details="Index: 6\nDescription: wlp2s0\nAlias: wlp2s0",
        ),
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
        Result(state=State.OK, notice="Non-Unicast in: 0 packets/s"),
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
        Result(state=State.OK, notice="Non-Unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]


@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_single_interface_group(  # type: ignore[misc]
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
def test_check_single_interface_group_admin_status(  # type: ignore[misc]
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
def test_check_single_interface_w_node(  # type: ignore[misc]
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
def test_check_single_interface_group_w_nodes(  # type: ignore[misc]
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
                "nucasts": {
                    "in": ("abs", (0.0, 5.0)),
                    "out": ("abs", (0.0, 5.0)),
                },
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
            details="Index: 1\nDescription: lo\nAlias: lo",
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
            summary="Non-Unicast in: 50 packets/s (warn/crit at 0 packets/s/5 packets/s)",
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
            summary="Non-Unicast out: 150 packets/s (warn/crit at 0 packets/s/5 packets/s)",
        ),
        Metric(
            "outnucast",
            150.0,
            levels=(0.0, 5.0),
        ),
    ]


def _interface_with_multicast_rates(
    *,
    speed: int,
    in_octets: float,
    out_octets: float = 0.0,
) -> interfaces.InterfaceWithRatesAndAverages:
    return interfaces.InterfaceWithRatesAndAverages(
        interfaces.Attributes(
            index="1",
            descr="lo",
            alias="lo",
            type="24",
            speed=speed,
            oper_status="1",
        ),
        interfaces.RatesWithAverages(
            in_octets=interfaces.RateWithAverage(in_octets, None),
            in_ucast=interfaces.RateWithAverage(180, None),
            in_mcast=interfaces.RateWithAverage(20, None),
            in_nucast=interfaces.RateWithAverage(20, None),
            out_octets=interfaces.RateWithAverage(out_octets, None),
            out_ucast=interfaces.RateWithAverage(180, None),
            out_mcast=interfaces.RateWithAverage(20, None),
            out_nucast=interfaces.RateWithAverage(20, None),
        ),
        get_rate_errors=[],
    )


def _multicast_entries(output: CheckResults, direction: str) -> CheckResults:
    return [
        entry
        for entry in output
        if (isinstance(entry, Metric) and entry.name == f"{direction}mcast")
        or (isinstance(entry, Result) and entry.details.startswith(f"Multicast {direction}"))
    ]


ONE_GBIT = 1000000000
ONE_GBIT_IN_BYTES_PER_SEC = ONE_GBIT / 8

MULTICAST_PERC_LEVELS = (5.0, 8.0)
MULTICAST_MIN_TRAFFIC = 5.0
MULTICAST_IN_CRIT = Result(state=State.CRIT, summary="Multicast in: 10% (warn/crit at 5%/8%)")
MULTICAST_LEVELS_ON_METRIC = (10.0, 16.0)


@pytest.mark.parametrize(
    "min_traffic, used_bandwidth_perc, expected",
    [
        pytest.param(None, None, (MULTICAST_PERC_LEVELS, ""), id="no minimum traffic configured"),
        pytest.param(None, 2.5, (MULTICAST_PERC_LEVELS, ""), id="no minimum traffic, low traffic"),
        pytest.param(5.0, 10.0, (MULTICAST_PERC_LEVELS, ""), id="minimum traffic exceeded"),
        pytest.param(5.0, 5.0, (MULTICAST_PERC_LEVELS, ""), id="minimum traffic exactly reached"),
        pytest.param(
            5.0,
            2.5,
            (None, " (levels not applied, used bandwidth below 5%)"),
            id="minimum traffic not reached",
        ),
        pytest.param(5.0, None, (MULTICAST_PERC_LEVELS, ""), id="used bandwidth unknown"),
        pytest.param(0.0, 0.0, (MULTICAST_PERC_LEVELS, ""), id="minimum traffic of zero"),
    ],
)
def test_percentual_packet_levels_evaluate(
    min_traffic: float | None,
    used_bandwidth_perc: float | None,
    expected: tuple[tuple[float, float] | None, str],
) -> None:
    levels = interfaces.PercentualPacketLevels(
        levels=MULTICAST_PERC_LEVELS,
        min_traffic=min_traffic,
    )
    assert levels.evaluate(used_bandwidth_perc) == expected


@pytest.mark.parametrize(
    "configured",
    [
        pytest.param(("nonsense", (5.0, 8.0)), id="unknown levels type"),
        pytest.param((5.0, 8.0), id="levels without a type"),
        pytest.param(("perc_min_traffic", (5.0, 8.0)), id="minimum traffic missing"),
    ],
)
def test_check_single_interface_rejects_unknown_packet_levels(configured: object) -> None:
    with pytest.raises(ValueError, match="Unknown multicast levels"):
        list(
            interfaces.check_single_interface(
                "1",
                {"multicast": {"in": configured}},
                _interface_with_multicast_rates(speed=ONE_GBIT, in_octets=0.0),
            )
        )


@pytest.mark.parametrize(
    "speed, in_octets, expected_result, expected_levels",
    [
        pytest.param(
            ONE_GBIT,
            0.1 * ONE_GBIT_IN_BYTES_PER_SEC,
            MULTICAST_IN_CRIT,
            MULTICAST_LEVELS_ON_METRIC,
            id="minimum traffic exceeded: levels applied",
        ),
        pytest.param(
            ONE_GBIT,
            0.05 * ONE_GBIT_IN_BYTES_PER_SEC,
            MULTICAST_IN_CRIT,
            MULTICAST_LEVELS_ON_METRIC,
            id="minimum traffic exactly reached: levels applied",
        ),
        pytest.param(
            ONE_GBIT,
            0.025 * ONE_GBIT_IN_BYTES_PER_SEC,
            Result(
                state=State.OK,
                notice="Multicast in: 10% (levels not applied, used bandwidth below 5%)",
            ),
            None,
            id="minimum traffic not reached: levels not applied",
        ),
        pytest.param(
            0,
            0.025 * ONE_GBIT_IN_BYTES_PER_SEC,
            MULTICAST_IN_CRIT,
            MULTICAST_LEVELS_ON_METRIC,
            id="unknown operating speed: levels applied",
        ),
    ],
)
def test_check_single_interface_perc_min_traffic(
    speed: int,
    in_octets: float,
    expected_result: Result,
    expected_levels: tuple[float, float] | None,
) -> None:
    output = list(
        interfaces.check_single_interface(
            "1",
            {
                "multicast": {
                    "in": ("perc_min_traffic", (*MULTICAST_PERC_LEVELS, MULTICAST_MIN_TRAFFIC))
                }
            },
            _interface_with_multicast_rates(speed=speed, in_octets=in_octets),
        )
    )
    assert _multicast_entries(output, "in") == [
        expected_result,
        Metric("inmcast", 20.0, levels=expected_levels),
    ]


MULTICAST_OUT_SUPPRESSED = Result(
    state=State.OK,
    notice="Multicast out: 10% (levels not applied, used bandwidth below 5%)",
)


def _assert_only_out_levels_suppressed(output: CheckResults) -> None:
    assert _multicast_entries(output, "in") == [
        MULTICAST_IN_CRIT,
        Metric("inmcast", 20.0, levels=MULTICAST_LEVELS_ON_METRIC),
    ]
    assert _multicast_entries(output, "out") == [
        MULTICAST_OUT_SUPPRESSED,
        Metric("outmcast", 20.0, levels=None),
    ]


def test_check_single_interface_perc_min_traffic_per_direction_traffic() -> None:
    _assert_only_out_levels_suppressed(
        list(
            interfaces.check_single_interface(
                "1",
                {
                    "multicast": {
                        "both": (
                            "perc_min_traffic",
                            (*MULTICAST_PERC_LEVELS, MULTICAST_MIN_TRAFFIC),
                        )
                    }
                },
                _interface_with_multicast_rates(
                    speed=ONE_GBIT,
                    in_octets=0.1 * ONE_GBIT_IN_BYTES_PER_SEC,
                    out_octets=0.025 * ONE_GBIT_IN_BYTES_PER_SEC,
                ),
            )
        )
    )


def test_check_single_interface_perc_min_traffic_per_direction_speed() -> None:
    _assert_only_out_levels_suppressed(
        list(
            interfaces.check_single_interface(
                "1",
                {
                    "assumed_speed_in": ONE_GBIT,
                    "assumed_speed_out": 4 * ONE_GBIT,
                    "multicast": {
                        "both": (
                            "perc_min_traffic",
                            (*MULTICAST_PERC_LEVELS, MULTICAST_MIN_TRAFFIC),
                        )
                    },
                },
                _interface_with_multicast_rates(
                    speed=ONE_GBIT,
                    in_octets=0.1 * ONE_GBIT_IN_BYTES_PER_SEC,
                    out_octets=0.1 * ONE_GBIT_IN_BYTES_PER_SEC,
                ),
            )
        )
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces(  # type: ignore[misc]
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
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0)
    assert (
        list(
            interfaces.check_multiple_interfaces(
                item,
                params,
                ifaces,
            )
        )
        == result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_descr(  # type: ignore[misc]
    item: str,
    params: Mapping[str, Any],
    result: CheckResults,
) -> None:
    description = "description"
    index = item
    item = f"{description} {item}"
    ifaces = _create_interfaces_with_counters(0, descr=description)
    list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0, descr=description)
    alias = ifaces[int(index) - 1].attributes.alias
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
        )
    ) == [
        Result(
            state=State.OK,
            summary=f"[{alias}]",
            details=f"Index: {index}\nDescription: {description}\nAlias: {alias}",
        ),
        *result[1:],
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_duplicate_alias(  # type: ignore[misc]
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
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0, alias=alias)
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
        )
    ) == [
        Result(
            state=State.OK,
            summary=f"[{alias}/{ifaces[int(index) - 1].attributes.descr}]",
            details=f"Index: {index}\n"
            f"Description: {ifaces[int(index) - 1].attributes.descr}\n"
            f"Alias: {alias}",
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
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0)
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
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
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0)
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
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
    list(interfaces.check_multiple_interfaces("group", params, ifaces))

    ifaces = _create_interfaces_with_counters(4000000, 5.0)
    ifaces[3].attributes.group = "group"
    ifaces[5].attributes.group = "group"
    assert list(interfaces.check_multiple_interfaces("group", params, ifaces)) == [
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
        Result(state=State.OK, notice="Non-Unicast in: 0 packets/s"),
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
        Result(state=State.OK, notice="Non-Unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_w_node(  # type: ignore[misc]
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
        )
    )
    ifaces = _create_interfaces_with_counters(4000000, 5.0, node=node_name)
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
        )
    ) == _add_node_name_to_results(result, node_name)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize("item, params, result", ITEM_PARAMS_RESULTS)
def test_check_multiple_interfaces_same_item_twice_cluster(  # type: ignore[misc]
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
        )
    )
    ifaces = [
        *_create_interfaces_with_counters(4000000, 5.0, node=node_name_1),
        *_create_interfaces_with_counters(4000000, 5.0, node=node_name_2),
    ]
    assert list(
        interfaces.check_multiple_interfaces(
            item,
            params,
            ifaces,
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
        )
    )
    ifaces = [
        interface
        for idx, node_name in enumerate(node_names)
        for interface in _create_interfaces_with_counters(
            4000000,
            5.0,
            admin_status=str(idx + 1),
            node=node_name,
        )
    ]
    assert list(
        interfaces.check_multiple_interfaces(
            "group",
            params,
            ifaces,
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
                        timestamp=0.0,
                    ),
                ],
            },
        )
    ) == [
        Result(
            state=State.OK,
            summary="[alias] on node",
            details="Index: 1\nDescription: descr\nAlias: alias\nNode: node",
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="Port 2",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="Port",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
def test_matching_interfaces_for_item[
    TInterfaceType: (interfaces.InterfaceWithCounters, interfaces.InterfaceWithRates)
](
    item: str,
    section: interfaces.Section[TInterfaceType],
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="1",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="",
                        alias="1",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
                ),
                interfaces.InterfaceWithCounters(
                    interfaces.Attributes(
                        index="2",
                        descr="1",
                        alias="",
                        type="10",
                    ),
                    interfaces.Counters(),
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
                    timestamp=0.0,
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
def test_matching_interfaces_for_item_clear_mixup_with_appearance[
    TInterfaceType: (interfaces.InterfaceWithCounters, interfaces.InterfaceWithRates)
](
    item: str,
    appearance: interfaces._ItemAppearance | None,
    section: interfaces.Section[TInterfaceType],
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
        timestamp=0.0,
    )
    value_store: dict[str, object] = {}

    # first call: value store initalization
    interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
        iface_with_counters,
        value_store=value_store,
        params={},
    )
    # second call: rate computation
    iface_with_rates_and_averages = (
        interfaces.InterfaceWithRatesAndAverages.from_interface_with_counters_or_rates(
            interfaces.InterfaceWithCounters(
                iface_with_counters.attributes,
                iface_with_counters.counters,
                timestamp=1.0,
            ),
            value_store=value_store,
            params={},
        )
    )

    assert list(interfaces.check_single_interface("1", {}, iface_with_rates_and_averages)) == [
        Result(
            state=State.OK,
            summary="[lo]",
            details="Index: 1\nDescription: lo\nAlias: lo",
        ),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="MAC: 00:00:00:00:00:00"),
        Result(state=State.OK, summary="Speed: unknown"),
        Result(state=State.OK, notice="Non-Unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Non-Unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
    ]
