#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Literal

import pytest

from cmk.ccc.hostaddress import HostName

from cmk.checkengine import value_store
from cmk.checkengine.checking import cluster_mode
from cmk.checkengine.plugins import CheckFunction, CheckPlugin, CheckPluginName, ServiceID

from cmk.agent_based.v2 import CheckResult, IgnoreResults, IgnoreResultsError, Metric, Result, State
from cmk.discover_plugins import PluginLocation

TEST_SERVICE_ID = ServiceID(CheckPluginName("unit_test_plugin"), "unit_test_item")


class _AllValueStoresStoreMocker(value_store.AllValueStoresStore):
    def __init__(self) -> None:
        super().__init__(Path(), log_debug=lambda x: None)

    def load(self) -> Mapping[value_store.ValueStoreKey, Mapping[str, str]]:
        return {}

    def update(self, update: object) -> None:
        pass


@pytest.fixture(name="vsm", scope="module")
def _vsm() -> value_store.ValueStoreManager:
    return value_store.ValueStoreManager(HostName("test-host"), _AllValueStoresStoreMocker())


def _get_test_check_plugin(**kwargs) -> CheckPlugin:  # type: ignore[no-untyped-def]
    return CheckPlugin(
        name=CheckPluginName("name"),
        sections=kwargs.get("sections", []),
        service_name="service_name",
        discovery_function=lambda *args, **kw: (),
        discovery_default_parameters=None,
        discovery_ruleset_name=None,
        discovery_ruleset_type="all",
        check_function=kwargs.get("check_function", lambda *args, **kw: object),
        cluster_check_function=kwargs.get("cluster_check_function", lambda *args, **kw: object),
        check_default_parameters=kwargs.get("check_default_parameters"),
        check_ruleset_name=kwargs.get("check_ruleset_name"),
        location=PluginLocation(module="module", name="name"),
    )


def _simple_check(section: Iterable[int]) -> CheckResult:
    """just a simple way to create test check results"""
    for value in section:
        try:
            yield Result(state=State(value), summary="Hi")
        except ValueError:
            if value == -1:
                yield IgnoreResults("yielded")
            elif value == -2:
                raise IgnoreResultsError("raised")
            else:
                yield Metric("n", value)


def _is_ok(*elements: object) -> bool:
    return State.worst(*(r.state for r in elements if isinstance(r, Result))) is State.OK


def test_get_cluster_check_function_native_missing(vsm: value_store.ValueStoreManager) -> None:
    plugin = _get_test_check_plugin(cluster_check_function=None)

    cc_function = cluster_mode.get_cluster_check_function(
        mode="native",
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        value_store_manager=vsm,
    )

    result = list(cc_function())[0]
    assert isinstance(result, Result) and result.state == State.UNKNOWN


def test_get_cluster_check_function_native_ok(vsm: value_store.ValueStoreManager) -> None:
    plugin = _get_test_check_plugin(cluster_check_function=_simple_check)

    cc_function = cluster_mode.get_cluster_check_function(
        mode="native",
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        value_store_manager=vsm,
    )

    assert cc_function is _simple_check


def _get_cluster_check_function(
    check_function: CheckFunction,
    *,
    mode: Literal["native", "failover", "worst", "best"],
    vsm: value_store.ValueStoreManager,
    clusterization_parameters: Mapping[str, Any] | None = None,
) -> Callable[..., Iterable[object]]:
    """small wrapper for cluster_mode.get_cluster_check_function"""
    plugin = _get_test_check_plugin(check_function=check_function)
    return cluster_mode.get_cluster_check_function(
        mode=mode,
        clusterization_parameters=clusterization_parameters or {},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        value_store_manager=vsm,
    )


def _simple_check_notice(section: Any) -> CheckResult:
    """just a simple way to create test check results"""
    yield Result(state=State.OK, notice="notice text moved to details")
    yield Result(
        state=State.OK, notice="This should be deleted from the output", details="yeah details"
    )


def test_notice_propagation_if_OK(vsm: value_store.ValueStoreManager) -> None:
    check_worst = _get_cluster_check_function(_simple_check_notice, mode="worst", vsm=vsm)
    assert list(
        check_worst(
            section={
                "Nodett": [],
            }
        )
    ) == [
        Result(state=State.OK, summary="Worst: [Nodett]"),
        Result(state=State.OK, notice="[Nodett]: notice text moved to details"),
        Result(state=State.OK, notice="[Nodett]: yeah details"),
    ]


def test_cluster_check_worst_item_not_found(vsm: value_store.ValueStoreManager) -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst", vsm=vsm)
    assert not list(
        check_worst(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_worst_ignore_results(vsm: value_store.ValueStoreManager) -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst", vsm=vsm)
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_worst(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_worst_others_are_notice_only(vsm: value_store.ValueStoreManager) -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst", vsm=vsm)

    assert list(
        check_worst(
            section={
                "Nodett": [2],
                "Nomo": [1],
            },
        )
    ) == [
        Result(state=State.OK, summary="Worst: [Nodett]"),
        Result(state=State.CRIT, summary="Hi", details="[Nodett]: Hi"),
        Result(state=State.OK, summary="Additional results from: [Nomo]"),
        Result(state=State.OK, notice="[Nomo]: Hi(!)"),
    ]


def test_cluster_check_worst_yield_worst_nodes_metrics(vsm: value_store.ValueStoreManager) -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst", vsm=vsm)

    assert list(
        m
        for m in check_worst(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric("n", 42)  # Nodeberts value


def test_cluster_check_worst_yield_selected_nodes_metrics(
    vsm: value_store.ValueStoreManager,
) -> None:
    check_worst = _get_cluster_check_function(
        _simple_check, mode="worst", vsm=vsm, clusterization_parameters={"metrics_node": "Nodett"}
    )

    assert list(
        m
        for m in check_worst(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric("n", 23)  # Nodetts value


def test_cluster_check_worst_unprefered_node_is_ok(vsm: value_store.ValueStoreManager) -> None:
    check_failover = _get_cluster_check_function(
        _simple_check, mode="worst", vsm=vsm, clusterization_parameters={"primary_node": "Nodebert"}
    )
    section = {"Nodett": [0]}

    assert _is_ok(*check_failover(section=section))


def test_cluster_check_best_item_not_found(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best", vsm=vsm)
    assert not list(
        check_best(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_best_ignore_results(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best", vsm=vsm)
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_best(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_best_empty_results_are_ignored(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best", vsm=vsm)

    assert list(
        check_best(
            section={"Nodett": [2], "Nomo": [1], "NoResults": []},
        )
    ) == [
        Result(state=State.OK, summary="Best: [Nomo]"),
        Result(state=State.WARN, summary="Hi", details="[Nomo]: Hi"),
        Result(state=State.OK, summary="Additional results from: [Nodett]"),
        Result(state=State.OK, notice="[Nodett]: Hi(!!)"),
    ]


def test_cluster_check_best_others_are_notice_only(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best", vsm=vsm)

    assert list(
        check_best(
            section={
                "Nodett": [2],
                "Nomo": [1],
            },
        )
    ) == [
        Result(state=State.OK, summary="Best: [Nomo]"),
        Result(state=State.WARN, summary="Hi", details="[Nomo]: Hi"),
        Result(state=State.OK, summary="Additional results from: [Nodett]"),
        Result(state=State.OK, notice="[Nodett]: Hi(!!)"),
    ]


def test_cluster_check_best_yield_best_nodes_metrics(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best", vsm=vsm)

    assert list(
        m
        for m in check_best(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric("n", 23)  # Nodetts value


def test_cluster_check_best_unprefered_node_is_ok(vsm: value_store.ValueStoreManager) -> None:
    check_failover = _get_cluster_check_function(
        _simple_check, mode="best", vsm=vsm, clusterization_parameters={"primary_node": "Nodebert"}
    )
    section = {"Nodett": [0]}

    assert _is_ok(*check_failover(section=section))


def test_cluster_check_failover_item_not_found(vsm: value_store.ValueStoreManager) -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="failover", vsm=vsm)
    assert not list(
        check_best(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_failover_ignore_results(vsm: value_store.ValueStoreManager) -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover", vsm=vsm)
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_failover(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_failover_others_are_notice_only(vsm: value_store.ValueStoreManager) -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover", vsm=vsm)

    assert list(
        check_failover(
            section={
                "Nodett": [2],
                "Nomo": [1],
            },
        )
    )[3:] == [
        Result(state=State.OK, notice="[Nomo]: Hi(!)"),
    ]


def test_cluster_check_failover_yield_worst_nodes_metrics(
    vsm: value_store.ValueStoreManager,
) -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover", vsm=vsm)

    assert list(
        m
        for m in check_failover(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric("n", 42)  # Nodeberts value.


def test_cluster_check_failover_two_are_not_ok(vsm: value_store.ValueStoreManager) -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover", vsm=vsm)
    section = {"Nodett": [0], "Nodebert": [0]}  # => everything ok, but to many results

    assert not _is_ok(*check_failover(section=section))


def test_cluster_check_failover_unprefered_node_is_not_ok(
    vsm: value_store.ValueStoreManager,
) -> None:
    check_failover = _get_cluster_check_function(
        _simple_check,
        mode="failover",
        vsm=vsm,
        clusterization_parameters={"primary_node": "Nodebert"},
    )
    section = {"Nodett": [0]}

    assert not _is_ok(*check_failover(section=section))


@pytest.mark.parametrize(
    "node_results, expected_primary_result, expected_secondary_result",
    [
        pytest.param(
            cluster_mode.NodeResults(
                results={
                    HostName("Nodebert"): [
                        Result(state=State.OK, notice="[Nodebert]: CPU load: 0.00")
                    ],
                    HostName("Nodett"): [Result(state=State.OK, notice="[Nodett]: CPU load: 0.00")],
                },
                metrics={
                    HostName("Nodebert"): [Metric("CPULoad", 0.00335345)],
                    HostName("Nodett"): [Metric("CPULoad", 0.00387467)],
                },
                ignore_results={HostName("Nodebert"): [], HostName("Nodett"): []},
            ),
            [
                Result(state=State.OK, summary="Best: [Nodebert]"),
                Result(state=State.OK, notice="[Nodebert]: CPU load: 0.00"),
            ],
            [
                Result(state=State.CRIT, summary="Additional results from: [Nodett]"),
                Result(state=State.OK, notice="[Nodett]: CPU load: 0.00"),
            ],
            id="notice only",
        ),
    ],
)
def test_summarizer_result_generation(
    node_results: cluster_mode.NodeResults,
    expected_primary_result: CheckResult,
    expected_secondary_result: CheckResult,
) -> None:
    clusterization_parameters = {"primary_node": HostName("Nodebert")}
    summarizer = cluster_mode.Summarizer(
        node_results=node_results,
        label="Best",
        selector=State.best,
        preferred=clusterization_parameters.get("primary_node"),
        unpreferred_node_state=State.WARN,
    )

    assert expected_primary_result == list(summarizer.primary_results())
    assert expected_secondary_result == list(
        summarizer.secondary_results(levels_additional_nodes_count=(0.0, 0.0))
    )
