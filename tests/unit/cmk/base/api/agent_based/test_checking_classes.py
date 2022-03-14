#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional, Tuple

import pytest

from cmk.base.api.agent_based.checking_classes import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    ServiceLabel,
)
from cmk.base.api.agent_based.checking_classes import State as state
from cmk.base.api.agent_based.type_defs import Parameters


@pytest.mark.parametrize(
    "data",
    [
        None,
        (),
        [],
        "",
    ],
)
def test_paramters_invalid(data):
    with pytest.raises(TypeError, match="expected dict"):
        _ = Parameters(data)


def test_parameters_features():
    par0 = Parameters({})
    par1 = Parameters({"olaf": "schneemann"})

    assert repr(par1) == "Parameters({'olaf': 'schneemann'})"

    assert len(par0) == 0
    assert len(par1) == 1

    assert not par0
    assert par1

    assert "olaf" not in par0
    assert "olaf" in par1

    assert par0.get("olaf") is None
    assert par1.get("olaf") == "schneemann"

    with pytest.raises(KeyError):
        _ = par0["olaf"]
    assert par1["olaf"] == "schneemann"

    assert list(par0) == list(par0.keys()) == list(par0.values()) == list(par0.items()) == []
    assert list(par1) == list(par1.keys()) == ["olaf"]
    assert list(par1.values()) == ["schneemann"]
    assert list(par1.items()) == [("olaf", "schneemann")]


def test_service_label():
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
def test_service_invalid(item, parameters, labels):
    with pytest.raises(TypeError):
        _ = Service(item=item, parameters=parameters, labels=labels)


def test_service_kwargs_only():
    with pytest.raises(TypeError):
        _ = Service(None)  # type: ignore[misc] # pylint: disable=too-many-function-args


def test_service_features():
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


def test_state():
    assert int(state.OK) == 0
    assert int(state.WARN) == 1
    assert int(state.CRIT) == 2
    assert int(state.UNKNOWN) == 3

    assert state.worst(state.WARN, state.UNKNOWN, state.CRIT) is state.CRIT
    assert state.worst(state.OK, state.WARN, state.UNKNOWN) is state.UNKNOWN
    assert state.worst(state.OK, state.WARN) is state.WARN
    assert state.worst(state.OK) is state.OK
    assert state.worst(state.OK, 3) is state.UNKNOWN

    assert state(0) is state.OK
    assert state(1) is state.WARN
    assert state(2) is state.CRIT
    assert state(3) is state.UNKNOWN

    assert state["OK"] is state.OK
    assert state["WARN"] is state.WARN
    assert state["CRIT"] is state.CRIT
    assert state["UNKNOWN"] is state.UNKNOWN

    with pytest.raises(TypeError):
        _ = state.OK < state.WARN  # type: ignore[operator]


@pytest.mark.parametrize(
    "states, best_state",
    [
        ((state.OK,), state.OK),
        ((state.OK, state.WARN), state.OK),
        ((state.OK, state.WARN, state.UNKNOWN), state.OK),
        ((state.OK, state.WARN, state.UNKNOWN, state.CRIT), state.OK),
        ((state.WARN,), state.WARN),
        ((state.WARN, state.UNKNOWN), state.WARN),
        ((state.WARN, state.UNKNOWN, state.CRIT), state.WARN),
        ((state.UNKNOWN,), state.UNKNOWN),
        ((state.UNKNOWN, state.CRIT), state.UNKNOWN),
        ((state.CRIT,), state.CRIT),
        ((0, 1, 2, 3, state.UNKNOWN), state.OK),
    ],
)
def test_best_state(states, best_state):
    assert state.best(*states) is best_state


def test_metric_kwarg():
    with pytest.raises(TypeError):
        _ = Metric("universe", 42, (23, 23))  # type: ignore[misc] # pylint: disable=too-many-function-args


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
def test_metric_invalid(name, value, levels, boundaries):
    with pytest.raises(TypeError):
        _ = Metric(name, value, levels=levels, boundaries=boundaries)


def test_metric():
    metric1 = Metric("reproduction_rate", 1.0, levels=(2.4, 3.0), boundaries=(0, None))
    metric2 = Metric("reproduction_rate", 2.0, levels=(2.4, 3.0), boundaries=(0, None))
    assert metric1.name == "reproduction_rate"
    assert metric1.value == 1.0
    assert metric1.levels == (2.4, 3.0)
    assert metric1.boundaries == (0.0, None)

    assert metric1 == metric1  # pylint: disable=comparison-with-itself
    assert metric1 != metric2


@pytest.mark.parametrize(
    "state_, summary, notice, details",
    [
        (8, "foo", None, None),
        (state.OK, b"foo", None, None),
        (state.OK, "newline is a \no-no", None, None),
        (state.OK, "", "", "details"),  # either is required
        (state.OK, None, None, "details"),  # either is required
        (state.OK, "these are", "mutually exclusive", None),
        (state.OK, "summary", None, {"at the moment": "impossible", "someday": "maybe"}),
    ],
)
def test_result_invalid(state_, summary, notice, details):
    with pytest.raises((TypeError, ValueError)):
        _ = Result(
            state=state_,
            summary=summary,
            notice=notice,
            details=details,
        )  # type: ignore[call-overload]


@pytest.mark.parametrize(
    "state_, summary, notice, details, expected_triple",
    [
        (state.OK, "summary", None, "details", (state.OK, "summary", "details")),
        (state.OK, "summary", None, None, (state.OK, "summary", "summary")),
        (state.OK, None, "notice", "details", (state.OK, "", "details")),
        (state.OK, None, "notice", None, (state.OK, "", "notice")),
        (state.WARN, "summary", None, "details", (state.WARN, "summary", "details")),
        (state.WARN, "summary", None, None, (state.WARN, "summary", "summary")),
        (state.WARN, None, "notice", "details", (state.WARN, "notice", "details")),
        (state.WARN, None, "notice", None, (state.WARN, "notice", "notice")),
    ],
)
def test_result(
    state_: state,
    summary: Optional[str],
    notice: Optional[str],
    details: Optional[str],
    expected_triple: Tuple[state, str, str],
) -> None:
    result = Result(
        state=state_,
        summary=summary,
        notice=notice,
        details=details,
    )  # type: ignore[call-overload]
    assert (result.state, result.summary, result.details) == expected_triple
    assert result != Result(state=state_, summary="a different summary")


def test_ignore_results():
    result1 = IgnoreResults()
    result2 = IgnoreResults("Login to DB failed")
    assert repr(result1) == "IgnoreResults('currently no results')"
    assert str(result2) == "Login to DB failed"
    assert result1 != result2
    assert result2 == IgnoreResults("Login to DB failed")
