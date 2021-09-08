#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# import pytest

from cmk.base.api.agent_based.checking_classes import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    State,
)
from cmk.base.api.agent_based.clusterize import make_node_notice_results

_OK_RESULT = Result(state=State.OK, summary="I am fine")

_WARN_RESULT = Result(state=State.WARN, summary="Watch out")


def _check_function_node(test_results):
    for res in test_results:
        yield res


def test_node_returns_nothing():
    assert list(make_node_notice_results("test_node", _check_function_node(()))) == []
    assert list(make_node_notice_results("test_node", ())) == []


def test_node_raises():
    def _check_node_raises():
        raise IgnoreResultsError()
        yield  # pylint: disable=unreachable

    assert list(make_node_notice_results("test_node", _check_node_raises())) == []


def test_node_ignore_results():
    node_results = _check_function_node((_OK_RESULT, IgnoreResults()))
    assert list(make_node_notice_results("test_node", node_results)) == []


def test_node_returns_metric():
    node_results = _check_function_node((_OK_RESULT, Metric("panic", 42)))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: I am fine"),
    ]


def test_node_returns_details_only():
    node_results = _check_function_node((Result(state=State.OK, notice="This is detailed"),))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: This is detailed"),
    ]


def test_node_returns_ok_and_warn():
    node_results = _check_function_node((_OK_RESULT, _WARN_RESULT))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: I am fine"),
        Result(state=State.WARN, notice="[test_node]: Watch out"),
    ]


def test_node_mutliline():
    node_results = (Result(state=State.WARN, notice="These\nare\nfour\nlines"),)
    assert list(make_node_notice_results("test_node", _check_function_node(node_results))) == [
        Result(
            state=State.WARN,
            summary="[test_node]: These, are, four, lines",
            details=(
                "[test_node]: These\n"
                "[test_node]: are\n"
                "[test_node]: four\n"
                "[test_node]: lines"
            ),
        ),
    ]
