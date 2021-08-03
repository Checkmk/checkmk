#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re
from typing import Iterable

import pytest

from cmk.utils.type_defs import CheckPluginName

import cmk.base.agent_based.checking._cluster_modes as cluster_modes
from cmk.base.api.agent_based.checking_classes import (
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
    return CheckPlugin(**{  # type: ignore[arg-type]
        **{
            'name': None,
            'sections': None,
            'service_name': None,
            'discovery_function': None,
            'discovery_default_parameters': None,
            'discovery_ruleset_name': None,
            'discovery_ruleset_type': None,
            'check_function': None,
            'check_default_parameters': None,
            'check_ruleset_name': None,
            'cluster_check_function': None,
            'module': None,
        },
        **kwargs,
    })


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


def test_get_cluster_check_function_native_missing():
    plugin = _get_test_check_plugin(cluster_check_function=None)

    cc_function = cluster_modes.get_cluster_check_function(
        mode='native',
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )

    result = list(cc_function())[0]
    assert isinstance(result, Result) and result.state == State.UNKNOWN


def test_get_cluster_check_function_native_ok():
    plugin = _get_test_check_plugin(cluster_check_function=_simple_check)

    cc_function = cluster_modes.get_cluster_check_function(
        mode='native',
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )

    assert cc_function is _simple_check


def _get_simple_check_worst_function(check_function):
    plugin = _get_test_check_plugin(check_function=check_function)
    return cluster_modes.get_cluster_check_function(
        mode='worst',
        clusterization_parameters={},
        service_id=TEST_SERVICE_ID,
        plugin=plugin,
        persist_value_store_changes=False,
    )


def test_cluster_check_worst_item_not_found():
    check_worst = _get_simple_check_worst_function(_simple_check)
    assert not list(check_worst(section={"Nodett": [], "Nomo": []},))


def test_cluster_check_worst_ignore_results():
    check_worst = _get_simple_check_worst_function(_simple_check)
    expected_msg = re.escape("[Nodett] yielded, [Nomo] raised")
    with pytest.raises(IgnoreResultsError, match=expected_msg):
        _ = list(check_worst(section={"Nodett": [-1], "Nomo": [-2]},))


def test_cluster_check_worst_others_are_notice_only():
    check_worst = _get_simple_check_worst_function(_simple_check)

    assert list(check_worst(section={
        "Nodett": [2],
        "Nomo": [1],
    },)) == [
        Result(state=State.CRIT, summary="[Nodett]: Hi"),
        Result(state=State.OK, notice="[Nomo]: Hi(!)"),
    ]


def test_cluster_check_worst_yield_worst_nodes_metrics():

    check_worst = _get_simple_check_worst_function(_simple_check)

    assert list(check_worst(section={
        "Nodett": [0, 23],
        "Nodebert": [1, 42],
    },)) == [
        Result(state=State.WARN, summary="[Nodebert]: Hi"),
        Result(state=State.OK, notice="[Nodett]: Hi"),
        Metric("n", 42),  # Nodeberts value.
    ]
