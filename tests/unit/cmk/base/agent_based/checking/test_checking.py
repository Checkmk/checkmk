#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.hostaddress import HostName

from cmk.checkengine.checkresults import ServiceCheckResult
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet

import cmk.base.agent_based.checking._checking as checking
import cmk.base.config as config
from cmk.base.api.agent_based.checking_classes import consume_check_results, Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult


def make_timespecific_params_list(
    entries: Iterable[LegacyCheckParameters],
) -> TimespecificParameters:
    return TimespecificParameters([TimespecificParameterSet.from_parameters(e) for e in entries])


@pytest.mark.parametrize(
    "rules,active_timeperiods,expected_result",
    [
        (make_timespecific_params_list([(1, 1), (2, 2)]), ["tp1", "tp2"], (1, 1)),
        (
            make_timespecific_params_list([(1, 1), {"tp_default_value": (2, 2), "tp_values": []}]),
            ["tp1", "tp2"],
            (1, 1),
        ),
        (
            make_timespecific_params_list([{"tp_default_value": (2, 2), "tp_values": []}, (1, 1)]),
            ["tp1", "tp2"],
            (2, 2),
        ),
        (
            make_timespecific_params_list(
                [{"tp_default_value": (2, 2), "tp_values": [("tp1", (3, 3))]}, (1, 1)]
            ),
            ["tp1", "tp2"],
            (3, 3),
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": (2, 2), "tp_values": [("tp2", (4, 4)), ("tp1", (3, 3))]},
                    (1, 1),
                ]
            ),
            ["tp1", "tp2"],
            (4, 4),
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": (2, 2), "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]},
                    (1, 1),
                ]
            ),
            ["tp2"],
            (2, 2),
        ),
        (
            make_timespecific_params_list(
                [
                    (1, 1),
                    {"tp_default_value": (2, 2), "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]},
                ]
            ),
            [],
            (1, 1),
        ),
        (make_timespecific_params_list([{1: 1}]), ["tp1", "tp2"], {1: 1}),
        (
            make_timespecific_params_list([{1: 1}, {"tp_default_value": {2: 2}, "tp_values": []}]),
            ["tp1", "tp2"],
            {1: 1, 2: 2},
        ),
        (
            make_timespecific_params_list(
                [{"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]}, {1: 1}]
            ),
            ["tp1", "tp2"],
            {1: 1, 2: 2, 3: 3},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp1", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1", "tp2"],
            {1: 5, 2: 4, 3: 6},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp3", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1", "tp2"],
            {1: 1, 2: 4, 3: 6},
        ),
        (
            make_timespecific_params_list(
                [
                    {"tp_default_value": {2: 4}, "tp_values": [("tp3", {1: 5}), ("tp2", {3: 6})]},
                    {"tp_default_value": {2: 2}, "tp_values": [("tp1", {3: 3})]},
                    {1: 1},
                ]
            ),
            ["tp1"],
            {1: 1, 2: 4, 3: 3},
        ),
        # (Old) tuple based default params
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {"key": (1, 1)},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            ["tp"],
            {"key": (2, 2)},
        ),
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {"key": (1, 1)},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            [],
            {"key": (1, 1)},
        ),
        (
            make_timespecific_params_list(
                [
                    {
                        "tp_default_value": {},
                        "tp_values": [
                            (
                                "tp",
                                {
                                    "key": (2, 2),
                                },
                            )
                        ],
                    },
                    (3, 3),
                ]
            ),
            [],
            {},
        ),
    ],
)
def test_time_resolved_check_parameters(
    monkeypatch: MonkeyPatch,
    rules: TimespecificParameters,
    active_timeperiods: Sequence[str],
    expected_result: LegacyCheckParameters,
) -> None:
    assert expected_result == rules.evaluate(lambda tp: tp in active_timeperiods)


@pytest.mark.parametrize(
    "subresults, aggregated_results",
    [
        ([], ServiceCheckResult.item_not_found()),
        (
            [
                Result(state=State.OK, notice="details"),
            ],
            ServiceCheckResult(0, "Everything looks OK - 1 detail available\ndetails", []),
        ),
        (
            [
                Result(state=State.OK, summary="summary1", details="detailed info1"),
                Result(state=State.WARN, summary="summary2", details="detailed info2"),
            ],
            ServiceCheckResult(1, "summary1, summary2(!)\ndetailed info1\ndetailed info2(!)", []),
        ),
        (
            [
                Result(state=State.OK, summary="summary"),
                Metric(name="name", value=42),
            ],
            ServiceCheckResult(0, "summary\nsummary", [("name", 42.0, None, None, None, None)]),
        ),
    ],
)
def test_aggregate_result(subresults: CheckResult, aggregated_results: ServiceCheckResult) -> None:
    assert checking._aggregate_results(consume_check_results(subresults)) == aggregated_results


def test_config_cache_get_clustered_service_node_keys_no_cluster(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    # empty, we have no cluster:
    assert [] == checking._get_clustered_service_node_keys(
        HostName("cluster.test"),
        SourceType.HOST,
        "Test Service",
        cluster_nodes=(),
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_cluster_no_service(
    monkeypatch: MonkeyPatch,
) -> None:
    cluster_test = HostName("cluster.test")
    ts = Scenario()
    ts.add_cluster(cluster_test, nodes=[HostName("node1.test"), HostName("node2.test")])

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    # empty for a node:
    assert [] == checking._get_clustered_service_node_keys(
        HostName("node1.test"),
        SourceType.HOST,
        "Test Service",
        cluster_nodes=(),
        get_effective_host=lambda hn, *args, **kw: hn,
    )

    # empty for cluster (we have not clustered the service)
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checking._get_clustered_service_node_keys(
        cluster_test,
        SourceType.HOST,
        "Test Service",
        cluster_nodes=[HostName("node1.test"), HostName("node2.test")],
        get_effective_host=lambda hn, *args, **kw: hn,
    )


def test_config_cache_get_clustered_service_node_keys_clustered(monkeypatch: MonkeyPatch) -> None:
    node1 = HostName("node1.test")
    node2 = HostName("node2.test")
    cluster = HostName("cluster.test")

    ts = Scenario()
    ts.add_host(node1)
    ts.add_host(node2)
    ts.add_cluster(cluster, nodes=[node1, node2])
    # add a fake rule, that defines a cluster
    ts.set_option(
        "clustered_services_mapping",
        [
            {
                "value": "cluster.test",
                "condition": {"service_description": ["Test Service"]},
            }
        ],
    )

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda hostname, *args, **kw: "dummy.test.ip.%s" % hostname[4],
    )
    assert checking._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        "Test Service",
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    ) == [
        HostKey(node1, SourceType.HOST),
        HostKey(node2, SourceType.HOST),
    ]
    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        lambda *args, **kw: "dummy.test.ip.0",
    )
    assert [
        HostKey(hostname=HostName("node1.test"), source_type=SourceType.HOST),
        HostKey(hostname=HostName("node2.test"), source_type=SourceType.HOST),
    ] == checking._get_clustered_service_node_keys(
        cluster,
        SourceType.HOST,
        "Test Unclustered",
        cluster_nodes=[node1, node2],
        get_effective_host=lambda hn, *args, **kw: hn,
    )
