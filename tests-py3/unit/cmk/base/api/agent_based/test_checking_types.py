#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from ast import literal_eval

import pytest  # type: ignore[import]

from cmk.base.api.agent_based.checking_types import (
    IgnoreResults,
    Parameters,
    ServiceLabel,
    Service,
    state,
    MetricFloat,
    Metric,
    Result,
)


@pytest.mark.parametrize("data", [
    None,
    (),
    [],
    "",
])
def test_paramters_invalid(data):
    with pytest.raises(TypeError, match="expected dict"):
        _ = Parameters(data)


def test_parameters_features():
    par0 = Parameters({})
    par1 = Parameters({'olaf': 'schneemann'})

    assert len(par0) == 0
    assert len(par1) == 1

    assert not par0
    assert par1

    assert 'olaf' not in par0
    assert 'olaf' in par1

    assert par0.get('olaf') is None
    assert par1.get('olaf') == 'schneemann'

    with pytest.raises(KeyError):
        _ = par0['olaf']
    assert par1['olaf'] == 'schneemann'

    assert list(par0) == list(par0.keys()) == list(par0.values()) == list(par0.items()) == []
    assert list(par1) == list(par1.keys()) == ['olaf']
    assert list(par1.values()) == ['schneemann']
    assert list(par1.items()) == [('olaf', 'schneemann')]


def test_service_label():
    # as far as the API is concerned, the only important thing ist that they
    # exist, an can be created like this.
    _ = ServiceLabel('from-home-office', 'true')


@pytest.mark.parametrize("item, parameters, labels", [
    (4, None, None),
    (None, (80, 90), None),
    (None, None, ()),
    (None, None, ["foo:bar"]),
])
def test_service_invalid(item, parameters, labels):
    with pytest.raises(TypeError):
        _ = Service(item=item, parameters=parameters, labels=labels)


def test_service_kwargs_only():
    with pytest.raises(TypeError):
        _ = Service(None)  # pylint: disable=too-many-function-args


def test_service_features():
    service = Service(
        item="thingy",
        parameters={"size": 42},
        labels=[ServiceLabel("test-thing", "true")],
    )

    assert service.item == "thingy"
    assert service.parameters == {"size": 42}
    assert service.labels == [ServiceLabel("test-thing", "true")]

    assert repr(service) == ("Service(item='thingy', parameters={'size': 42},"
                             " labels=[ServiceLabel('test-thing', 'true')])")

    service = Service()
    assert service.item is None
    assert service.parameters == {}
    assert service.labels == []
    assert repr(service) == "Service(item=None, parameters={}, labels=[])"


def test_state():
    assert state(0) is state.OK
    assert state.OK == 0

    assert state(1) is state.WARN
    assert state.WARN == 1

    assert state(2) is state.CRIT
    assert state.CRIT == 2

    assert state(3) is state.UNKNOWN
    assert state.UNKNOWN == 3


def test_metric_float():
    inf = MetricFloat('inf')
    assert literal_eval("%r" % inf) == float('inf')


def test_metric_kwarg():
    with pytest.raises(TypeError):
        _ = Metric("universe", 42, (23, 23))  # py # lint: disable=too-many-function-args


@pytest.mark.parametrize("name, value, levels, boundaries", [
    ("name", "7", (None, None), (None, None)),
    ("n me", "7", (None, None), (None, None)),
    ("n=me", "7", (None, None), (None, None)),
    ("name", 7, (23, 42), None),
    ("name", 7, ("warn", "crit"), (None, None)),
    ("name", 7, (23, 42), (None, "max")),
])
def test_metric_invalid(name, value, levels, boundaries):
    with pytest.raises(TypeError):
        _ = Metric(name, value, levels=levels, boundaries=boundaries)


def test_metric():
    metric1 = Metric('reproduction_rate', 1.0, levels=(2.4, 3.0), boundaries=(0, None))
    metric2 = Metric('reproduction_rate', 2.0, levels=(2.4, 3.0), boundaries=(0, None))
    assert metric1.name == 'reproduction_rate'
    assert metric1.value == 1.0
    assert metric1.levels == (2.4, 3.0)
    assert metric1.boundaries == (0., None)

    assert metric1 == metric1  # pylint: disable=comparison-with-itself
    assert metric1 != metric2


@pytest.mark.parametrize(
    "state_, summary, details",
    [
        (8, "foo", None),
        (state.OK, b"foo", None),
        (state.OK, "newline is a \no-no", None),
        (state.OK, "", ""),  # either is required
        (state.OK, "", None),  # either is required
        (state.OK, None, ""),  # either is required
        (state.OK, None, None),  # either is required
        (state.OK, "this is longer than the", "detailed variant"),
        (state.OK, "summary", {
            "at the moment": "impossible",
            "someday": "maybe"
        }),
    ])
def test_result_invalid(state_, summary, details):
    with pytest.raises((TypeError, ValueError)):
        _ = Result(state=state_, summary=summary, details=details)


def test_result():
    result = Result(state=state.OK,
                    summary="moooo",
                    details="I'm a cow and I will chill out all day.")
    assert result.state == state.OK
    assert result.summary == "moooo"
    assert result.details == "I'm a cow and I will chill out all day."

    result = Result(summary="info", details="")
    assert result.state is None
    assert result.summary == "info"
    assert result.details is None


def test_ignore_results():
    # This is just a plain object. Nothing to test, but it should exist.
    assert isinstance(IgnoreResults(), object)
