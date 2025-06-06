#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# import pytest

from collections.abc import Iterable

from cmk.agent_based.v1 import IgnoreResults, IgnoreResultsError, Metric, Result, State
from cmk.agent_based.v1.clusterize import make_node_notice_results

_OK_RESULT = Result(state=State.OK, summary="I am fine")

_WARN_RESULT = Result(state=State.WARN, summary="Watch out")


def _check_function_node(
    test_results: Iterable[Result | Metric | IgnoreResults],
) -> Iterable[Result | Metric | IgnoreResults]:
    yield from test_results


def test_node_returns_nothing() -> None:
    assert not list(make_node_notice_results("test_node", _check_function_node(())))
    assert not list(make_node_notice_results("test_node", ()))


def test_node_raises() -> None:
    def _check_node_raises() -> Iterable[IgnoreResults]:
        yield from ()
        raise IgnoreResultsError()

    assert not list(make_node_notice_results("test_node", _check_node_raises()))


def test_node_ignore_results() -> None:
    node_results = _check_function_node((_OK_RESULT, IgnoreResults()))
    assert not list(make_node_notice_results("test_node", node_results))


def test_node_returns_metric() -> None:
    node_results = _check_function_node((_OK_RESULT, Metric("panic", 42)))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: I am fine"),
    ]


def test_node_returns_details_only() -> None:
    node_results = _check_function_node((Result(state=State.OK, notice="This is detailed"),))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: This is detailed"),
    ]


def test_node_returns_ok_and_warn() -> None:
    node_results = _check_function_node((_OK_RESULT, _WARN_RESULT))
    assert list(make_node_notice_results("test_node", node_results)) == [
        Result(state=State.OK, notice="[test_node]: I am fine"),
        Result(state=State.WARN, notice="[test_node]: Watch out"),
    ]


def test_node_mutliline() -> None:
    node_results = (Result(state=State.WARN, notice="These\nare\nfour\nlines"),)
    assert list(make_node_notice_results("test_node", _check_function_node(node_results))) == [
        Result(
            state=State.WARN,
            summary="[test_node]: These, are, four, lines",
            details=("[test_node]: These\n[test_node]: are\n[test_node]: four\n[test_node]: lines"),
        ),
    ]
