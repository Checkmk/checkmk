#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.gui.monitor.hosts._api._filters import (
    AndNode,
    FilterNode,
    LabelChoiceCondition,
    StringCondition,
    StringField,
)
from cmk.gui.monitor.hosts.search_filters import host_search_filter, UnsupportedSearchError
from cmk.gui.search.spec import parse, PrefixedSearch


def _filter(query: str) -> FilterNode:
    spec = parse(query)
    assert isinstance(spec, PrefixedSearch)
    return host_search_filter(spec)


def _contains(field: StringField, value: str) -> StringCondition:
    return StringCondition(type="condition", field=field, op="contains", value=value)


def _all_of(field: Literal["labels", "tags"], *pairs: str) -> LabelChoiceCondition:
    return LabelChoiceCondition(type="condition", field=field, op="all_of", value=list(pairs))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("h:web", _contains("name", "web"), id="h"),
        pytest.param("al:db*", _contains("alias", "db.*"), id="al"),
        pytest.param("ad:10.", _contains("address", "10."), id="ad"),
        pytest.param("hl:os:linux", _all_of("labels", "os:linux"), id="hl"),
        pytest.param("tg:criticality:prod", _all_of("tags", "criticality:prod"), id="tg"),
        pytest.param("h:a h:b", _contains("name", "a|b"), id="repeated-pattern"),
        pytest.param("hl:os:lin*", _all_of("labels", "os:lin*"), id="hl-prefix"),
        pytest.param("hl:cmk/aws*", _all_of("labels", "cmk/aws*"), id="hl-key-prefix"),
        pytest.param("tg:os:lin*", _all_of("tags", "os:lin*"), id="tg-prefix"),
    ],
)
def test_clause_becomes_one_condition(query: str, expected: FilterNode) -> None:
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, children",
    [
        pytest.param(
            "h:web ad:10.", [_contains("name", "web"), _contains("address", "10.")], id="prefixes"
        ),
        pytest.param(
            "hl:os:linux h:web tg:dc:fra hl:env:prod",
            [
                _all_of("labels", "os:linux", "env:prod"),
                _contains("name", "web"),
                _all_of("tags", "dc:fra"),
            ],
            id="labels-and-tags",
        ),
    ],
)
def test_clauses_are_top_level_and_conditions(query: str, children: list[FilterNode]) -> None:
    assert _filter(query) == AndNode(type="and", children=children)


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:os:linux hl:env:prod", _all_of("labels", "os:linux", "env:prod"), id="hl"),
        pytest.param("tg:dc:fra tg:os:lin*", _all_of("tags", "dc:fra", "os:lin*"), id="tg"),
        pytest.param("hl:os:linux hl:os:linux", _all_of("labels", "os:linux"), id="repeated-pair"),
    ],
)
def test_labels_or_tags_are_one_condition_with_every_pair(query: str, expected: FilterNode) -> None:
    # A column filter shows a single condition per field. "all_of" ands the pairs like the clauses.
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("tg:prod", "Please specify the tag group", id="tag-without-group"),
        pytest.param("s:cpu", "can only be searched by", id="service"),
        pytest.param("h:web s:cpu", "can only be searched by", id="host-and-service"),
        pytest.param("hg:linux", "can only be searched by", id="host-group"),
    ],
)
def test_spec_all_hosts_cannot_filter_on_is_rejected(query: str, message: str) -> None:
    with pytest.raises(UnsupportedSearchError, match=message):
        _filter(query)
