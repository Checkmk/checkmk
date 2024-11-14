#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from ast import literal_eval
from collections.abc import Sequence

import pytest

from cmk.agent_based.v1 import IgnoreResults, Metric, Result, Service, ServiceLabel, State
from cmk.agent_based.v1._checking_classes import _EvalableFloat


def test_evalable_float() -> None:
    inf = _EvalableFloat("inf")
    assert literal_eval(f"{inf!r}") == float("inf")


def test_service_label() -> None:
    # as far as the API is concerned, the only important thing ist that they
    # exist, an can be created like this.
    _ = ServiceLabel("from-home-office", "true")


@pytest.mark.parametrize(
    "item, parameters, labels",
    [
        (4, None, None),
        (None, (80, 90), None),
        (None, None, ["foo:bar"]),
    ],
)
def test_service_invalid(item: object, parameters: object, labels: object) -> None:
    with pytest.raises(TypeError):
        _ = Service(item=item, parameters=parameters, labels=labels)  # type: ignore[arg-type]


def test_service_kwargs_only() -> None:
    with pytest.raises(TypeError):
        _ = Service(None)  # type: ignore[misc]


def test_service_features() -> None:
    service = Service(
        item="thingy",
        parameters={"size": 42},
        labels=[ServiceLabel("test-thing", "true")],
    )

    assert service.item == "thingy"
    assert service.parameters == {"size": 42}
    assert service.labels == [ServiceLabel("test-thing", "true")]

    assert repr(service) == (
        "Service(item='thingy', parameters={'size': 42},"
        " labels=[ServiceLabel('test-thing', 'true')])"
    )

    service = Service()
    assert service.item is None
    assert service.parameters == {}
    assert service.labels == []
    assert repr(service) == "Service()"

    service_foo = Service(item="foo")
    assert repr(service_foo) == "Service(item='foo')"

    assert service != service_foo


def test_state() -> None:
    assert int(State.OK) == 0
    assert int(State.WARN) == 1
    assert int(State.CRIT) == 2
    assert int(State.UNKNOWN) == 3

    assert State.worst(State.WARN, State.UNKNOWN, State.CRIT) is State.CRIT
    assert State.worst(State.OK, State.WARN, State.UNKNOWN) is State.UNKNOWN
    assert State.worst(State.OK, State.WARN) is State.WARN
    assert State.worst(State.OK) is State.OK
    assert State.worst(State.OK, 3) is State.UNKNOWN

    assert State(0) is State.OK
    assert State(1) is State.WARN
    assert State(2) is State.CRIT
    assert State(3) is State.UNKNOWN

    assert State["OK"] is State.OK
    assert State["WARN"] is State.WARN
    assert State["CRIT"] is State.CRIT
    assert State["UNKNOWN"] is State.UNKNOWN

    with pytest.raises(TypeError):
        _ = State.OK < State.WARN  # type: ignore[operator]


@pytest.mark.parametrize(
    "states, best_state",
    [
        ((State.OK,), State.OK),
        ((State.OK, State.WARN), State.OK),
        ((State.OK, State.WARN, State.UNKNOWN), State.OK),
        ((State.OK, State.WARN, State.UNKNOWN, State.CRIT), State.OK),
        ((State.WARN,), State.WARN),
        ((State.WARN, State.UNKNOWN), State.WARN),
        ((State.WARN, State.UNKNOWN, State.CRIT), State.WARN),
        ((State.UNKNOWN,), State.UNKNOWN),
        ((State.UNKNOWN, State.CRIT), State.UNKNOWN),
        ((State.CRIT,), State.CRIT),
        ((0, 1, 2, 3, State.UNKNOWN), State.OK),
    ],
)
def test_best_state(
    states: Sequence[State],
    best_state: State,
) -> None:
    assert State.best(*states) is best_state


def test_metric_kwarg() -> None:
    with pytest.raises(TypeError):
        _ = Metric("universe", 42, (23, 23))  # type: ignore[misc]


@pytest.mark.parametrize(
    "name, value, levels, boundaries",
    [
        ("", 7, None, None),
        ("name", "7", (None, None), (None, None)),
        ("n me", "7", (None, None), (None, None)),
        ("n=me", "7", (None, None), (None, None)),
        ("name", 7, ("warn", "crit"), (None, None)),
        ("name", 7, (23, 42), (None, "max")),
    ],
)
def test_metric_invalid(name: object, value: object, levels: object, boundaries: object) -> None:
    with pytest.raises(TypeError):
        _ = Metric(name, value, levels=levels, boundaries=boundaries)  # type: ignore[arg-type]


def test_metric() -> None:
    metric1 = Metric("reproduction_rate", 1.0, levels=(2.4, 3.0), boundaries=(0, None))
    metric2 = Metric("reproduction_rate", 2.0, levels=(2.4, 3.0), boundaries=(0, None))
    assert metric1.name == "reproduction_rate"
    assert metric1.value == 1.0
    assert metric1.levels == (2.4, 3.0)
    assert metric1.boundaries == (0.0, None)

    assert metric1 == metric1  # noqa: PLR0124
    assert metric1 != metric2


@pytest.mark.parametrize(
    "state_, summary, notice, details",
    [
        (8, "foo", None, None),
        (State.OK, b"foo", None, None),
        (State.OK, "newline is a \no-no", None, None),
        (State.OK, "", "", "details"),  # either is required
        (State.OK, None, None, "details"),  # either is required
        (State.OK, "these are", "mutually exclusive", None),
        (State.OK, "summary", None, {"at the moment": "impossible", "someday": "maybe"}),
    ],
)
def test_result_invalid(state_: object, summary: object, notice: object, details: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        _: Result = Result(
            state=state_,
            summary=summary,
            notice=notice,
            details=details,
        )  # type: ignore[call-overload]


@pytest.mark.parametrize(
    "state_, summary, notice, details, expected_triple",
    [
        (State.OK, "summary", None, "details", (State.OK, "summary", "details")),
        (State.OK, "summary", None, None, (State.OK, "summary", "summary")),
        (State.OK, None, "notice", "details", (State.OK, "", "details")),
        (State.OK, None, "notice", None, (State.OK, "", "notice")),
        (State.WARN, "summary", None, "details", (State.WARN, "summary", "details")),
        (State.WARN, "summary", None, None, (State.WARN, "summary", "summary")),
        (State.WARN, None, "notice", "details", (State.WARN, "notice", "details")),
        (State.WARN, None, "notice", None, (State.WARN, "notice", "notice")),
    ],
)
def test_result(
    state_: State,
    summary: str | None,
    notice: str | None,
    details: str | None,
    expected_triple: tuple[State, str, str],
) -> None:
    result: Result = Result(
        state=state_,
        summary=summary,
        notice=notice,
        details=details,
    )  # type: ignore[call-overload]
    assert (result.state, result.summary, result.details) == expected_triple
    assert result != Result(state=state_, summary="a different summary")


def test_ignore_results() -> None:
    result1 = IgnoreResults()
    result2 = IgnoreResults("Login to DB failed")
    assert repr(result1) == "IgnoreResults('currently no results')"
    assert str(result2) == "Login to DB failed"
    assert result1 != result2
    assert result2 == IgnoreResults("Login to DB failed")
