#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#import pytest  # type: ignore[import]

from cmk.base.api.agent_based.checking_types import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    state,
)
from cmk.base.api.agent_based.clusterize import aggregate_node_details

_OK_RESULT = Result(state=state.OK, summary="I am fine")

_WARN_RESULT = Result(state=state.WARN, summary="Watch out")


def _check_function_node(test_results):
    for res in test_results:
        yield res


def test_node_returns_nothing():
    assert aggregate_node_details("test_node", _check_function_node(())) is None
    assert aggregate_node_details("test_node", ()) is None


def test_node_raises():
    def _check_node_raises():
        raise IgnoreResultsError()
        yield  # pylint: disable=unreachable

    assert aggregate_node_details("test_node", _check_node_raises()) is None


def test_node_ignore_results():
    node_results = _check_function_node((_OK_RESULT, IgnoreResults()))
    assert aggregate_node_details("test_node", node_results) is None


def test_node_returns_metric():
    node_results = _check_function_node((_OK_RESULT, Metric("panic", 42)))
    result = aggregate_node_details("test_node", node_results)
    assert result is not None
    assert result.state is state.OK
    assert result.summary == ""
    assert result.details == "[test_node]: I am fine"


def test_node_returns_details_only():
    node_results = _check_function_node((Result(state=state.OK, details="This is detailed"),))
    result = aggregate_node_details("test_node", node_results)
    assert result is not None
    assert result.state is state.OK
    assert result.summary == ""
    assert result.details == "[test_node]: This is detailed"


def test_node_returns_ok_and_warn():
    node_results = _check_function_node((_OK_RESULT, _WARN_RESULT))
    result = aggregate_node_details("test_node", node_results)
    assert result is not None
    assert result.state is state.WARN
    assert result.summary == ""
    assert result.details == (
        "[test_node]: I am fine\n"  #
        "[test_node]: Watch out(!)")


def test_node_mutliline():
    node_results = (Result(state=state.WARN, details="These\nare\nfour\nlines"),)
    result = aggregate_node_details("test_node", _check_function_node(node_results))
    assert result is not None
    assert result.state is state.WARN
    assert result.summary == ""
    assert result.details == ("[test_node]: These\n"
                              "[test_node]: are\n"
                              "[test_node]: four\n"
                              "[test_node]: lines(!)")
