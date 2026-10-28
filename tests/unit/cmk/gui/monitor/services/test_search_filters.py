#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.monitor.services._api._filters import (
    ServiceAndNode,
    ServiceFilterNode,
    ServiceLabelChoiceCondition,
    ServiceNameChoiceCondition,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
)
from cmk.gui.monitor.services._models import ServiceStateLabel
from cmk.gui.monitor.services.search_filters import service_search_filter
from cmk.gui.search.spec import parse, PrefixedSearch, UnsupportedSearchError


def _filter(query: str) -> ServiceFilterNode:
    spec = parse(query)
    assert isinstance(spec, PrefixedSearch)
    return service_search_filter(spec)


def _contains(field: Literal["name", "host_name"], value: str) -> ServiceStringCondition:
    return ServiceStringCondition(type="condition", field=field, op="contains", value=value)


def _states(*states: ServiceStateLabel) -> ServiceStateChoiceCondition:
    return ServiceStateChoiceCondition(
        type="condition", field="state", op="one_of", value=list(states)
    )


def _labels(*pairs: str) -> ServiceLabelChoiceCondition:
    return ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=list(pairs)
    )


def _groups(*names: str) -> ServiceNameChoiceCondition:
    return ServiceNameChoiceCondition(
        type="condition", field="groups", op="one_of", value=list(names)
    )


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("s:cpu", _contains("name", "cpu"), id="s"),
        pytest.param("s:cpu s:mem*", _contains("name", "cpu|mem.*"), id="s-or-ed"),
        pytest.param("st:crit", _states("CRIT"), id="st"),
        pytest.param(
            "st:ok|warn st:unkn st:pend",
            _states("OK", "WARN", "UNKNOWN", "PENDING"),
            id="st-or-ed",
        ),
        pytest.param("st:warn st:warn", _states("WARN"), id="st-repeated"),
        pytest.param("sl:os:linux", _labels("os:linux"), id="sl"),
        pytest.param("sl:cmk/aws*", _labels("cmk/aws*"), id="sl-key-prefix"),
        pytest.param("sl:os:*", _labels("os:*"), id="sl-any-value"),
        pytest.param("sg:web sg:db*", _groups("web", "db*"), id="sg"),
    ],
)
def test_clause_becomes_one_condition(query: str, expected: ServiceFilterNode) -> None:
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, children",
    [
        pytest.param(
            "h:web s:cpu",
            [_contains("host_name", "web"), _contains("name", "cpu")],
            id="host-and-service",
        ),
        pytest.param(
            "sl:os:linux st:crit sl:env:prod",
            [_labels("os:linux", "env:prod"), _states("CRIT")],
            id="labels",
        ),
    ],
)
def test_clauses_are_top_level_and_conditions(
    query: str, children: list[ServiceFilterNode]
) -> None:
    assert _filter(query) == ServiceAndNode(type="and", children=children)


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("s:cpu al:web", id="host-alias"),
        pytest.param("s:cpu hl:os:linux", id="host-label"),
        pytest.param("s:cpu tg:criticality:prod", id="host-tag"),
        pytest.param("sf:linux", id="service-folder"),
    ],
)
def test_spec_all_services_cannot_filter_on_is_rejected(query: str) -> None:
    with pytest.raises(UnsupportedSearchError, match="can only be searched by"):
        _filter(query)
