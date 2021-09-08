#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re
from typing import Any, Iterable, Literal, Mapping, Optional, Union

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.agent_based.checking import _cluster_modes as cluster_modes
from cmk.base.api.agent_based.checking_classes import (
    CheckFunction,
    CheckPlugin,
    CheckResult,
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    State,
)

TEST_SERVICE_ID = (CheckPluginName("unit_test_plugin"), "unit_test_item")


def _get_test_check_plugin(**kwargs) -> CheckPlugin:
    return CheckPlugin(
        **{  # type: ignore[arg-type]
            **{
                "name": None,
                "sections": None,
                "service_name": None,
                "discovery_function": None,
                "discovery_default_parameters": None,
                "discovery_ruleset_name": None,
                "discovery_ruleset_type": None,
                "check_function": None,
                "check_default_parameters": None,
                "check_ruleset_name": None,
                "cluster_check_function": None,
                "module": None,
            },
            **kwargs,
        }
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


def _is_ok(*elements: Union[Result, Metric, IgnoreResults]) -> bool:
    return State.worst(*(r.state for r in elements if isinstance(r, Result))) is State.OK


def test_get_cluster_check_function_native_missing() -> None:
    plugin = _get_test_check_plugin(cluster_check_function=None)

    cc_function = cluster_modes.get_cluster_check_function(
        mode="native",
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )

    result = list(cc_function())[0]
    assert isinstance(result, Result) and result.state == State.UNKNOWN


def test_get_cluster_check_function_native_ok() -> None:
    plugin = _get_test_check_plugin(cluster_check_function=_simple_check)

    cc_function = cluster_modes.get_cluster_check_function(
        mode="native",
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )

    assert cc_function is _simple_check


def _get_cluster_check_function(
    check_function: CheckFunction,
    *,
    mode: Literal["native", "failover", "worst", "best"],
    clusterization_parameters: Optional[Mapping[ſtr, Any]] = None,
) -> CheckFunction:
    """small wrapper for cluster_modes.get_cluster_check_function"""
    plugin = _get_test_check_plugin(check_function=check_function)
    return cluster_modes.get_cluster_check_function(
        mode=mode,
        clusterization_parameters=clusterization_parameters or {},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )


def test_cluster_check_worst_item_not_found() -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst")
    assert not list(
        check_worst(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_worst_ignore_results() -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst")
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_worst(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_worst_others_are_notice_only() -> None:
    check_worst = _get_cluster_check_function(_simple_check, mode="worst")

    assert list(check_worst(section={"Nodett": [2], "Nomo": [1],},)) == [
        Result(state=State.OK, summary="Worst: [Nodett]"),
        Result(state=State.CRIT, summary="Hi", details="[Nodett]: Hi"),
        Result(state=State.OK, summary="Additional results from: [Nomo]"),
        Result(state=State.OK, notice="[Nomo]: Hi(!)"),
    ]


def test_cluster_check_worst_yield_worst_nodes_metrics() -> None:

    check_worst = _get_cluster_check_function(_simple_check, mode="worst")

    assert list(
        m
        for m in check_worst(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric(
        "n", 42
    )  # Nodeberts value


def test_cluster_check_worst_yield_selected_nodes_metrics() -> None:

    check_worst = _get_cluster_check_function(
        _simple_check, mode="worst", clusterization_parameters={"metrics_node": "Nodett"}
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
    )[0] == Metric(
        "n", 23
    )  # Nodetts value


def test_cluster_check_worst_unprefered_node_is_ok() -> None:

    check_failover = _get_cluster_check_function(
        _simple_check, mode="worst", clusterization_parameters={"primary_node": "Nodebert"}
    )
    section = {"Nodett": [0]}

    assert _is_ok(*check_failover(section=section))


def test_cluster_check_best_item_not_found() -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best")
    assert not list(
        check_best(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_best_ignore_results() -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best")
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_best(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_best_others_are_notice_only() -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="best")

    assert list(check_best(section={"Nodett": [2], "Nomo": [1],},)) == [
        Result(state=State.OK, summary="Best: [Nomo]"),
        Result(state=State.WARN, summary="Hi", details="[Nomo]: Hi"),
        Result(state=State.OK, summary="Additional results from: [Nodett]"),
        Result(state=State.OK, notice="[Nodett]: Hi(!!)"),
    ]


def test_cluster_check_best_yield_best_nodes_metrics() -> None:

    check_best = _get_cluster_check_function(_simple_check, mode="best")

    assert list(
        m
        for m in check_best(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric(
        "n", 23
    )  # Nodetts value


def test_cluster_check_best_unprefered_node_is_ok() -> None:

    check_failover = _get_cluster_check_function(
        _simple_check, mode="best", clusterization_parameters={"primary_node": "Nodebert"}
    )
    section = {"Nodett": [0]}

    assert _is_ok(*check_failover(section=section))


def test_cluster_check_failover_item_not_found() -> None:
    check_best = _get_cluster_check_function(_simple_check, mode="failover")
    assert not list(
        check_best(
            section={"Nodett": [], "Nomo": []},
        )
    )


def test_cluster_check_failover_ignore_results() -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover")
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(
            check_failover(
                section={"Nodett": [-1], "Nomo": [-2]},
            )
        )


def test_cluster_check_failover_others_are_notice_only() -> None:
    check_failover = _get_cluster_check_function(_simple_check, mode="failover")

    assert list(check_failover(section={"Nodett": [2], "Nomo": [1],},))[3:] == [
        Result(state=State.OK, notice="[Nomo]: Hi(!)"),
    ]


def test_cluster_check_failover_yield_worst_nodes_metrics() -> None:

    check_failover = _get_cluster_check_function(_simple_check, mode="failover")

    assert list(
        m
        for m in check_failover(
            section={
                "Nodett": [0, 23],
                "Nodebert": [1, 42],
            },
        )
        if isinstance(m, Metric)
    )[0] == Metric(
        "n", 42
    )  # Nodeberts value.


def test_cluster_check_failover_two_are_not_ok() -> None:

    check_failover = _get_cluster_check_function(_simple_check, mode="failover")
    section = {"Nodett": [0], "Nodebert": [0]}  # => everything ok, but to many results

    assert not _is_ok(*check_failover(section=section))


def test_cluster_check_failover_unprefered_node_is_not_ok() -> None:

    check_failover = _get_cluster_check_function(
        _simple_check, mode="failover", clusterization_parameters={"primary_node": "Nodebert"}
    )
    section = {"Nodett": [0]}

    assert not _is_ok(*check_failover(section=section))
