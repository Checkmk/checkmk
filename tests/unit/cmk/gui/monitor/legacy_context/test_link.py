#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from urllib.parse import urlencode

from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.monitor.legacy_context import (
    build_column_filter_check,
    build_link_url,
    ContextFilterTranslation,
    encode_unapplied_filters,
    read_unapplied_filter_titles,
)
from cmk.gui.type_defs import FilterName, VisualContext

_TITLES = {"wato_folder": "Folder", "hostgroup": "Host group"}


def _request(vars_: list[tuple[str, str]]) -> Request:
    return Request(create_environ(query_string=urlencode(vars_)))


def test_a_link_that_took_over_every_filter_names_none() -> None:
    assert encode_unapplied_filters([]) == []


def test_the_page_names_by_their_titles_the_filters_a_link_could_not_take_over() -> None:
    request = _request(encode_unapplied_filters(["wato_folder", "hostgroup"]))

    assert read_unapplied_filter_titles(request, _TITLES.get) == [
        ("wato_folder", "Folder"),
        ("hostgroup", "Host group"),
    ]


def test_the_page_names_no_filter_that_does_not_exist() -> None:
    request = _request([("unapplied", "wato_folder,Click here!")])

    assert read_unapplied_filter_titles(request, _TITLES.get) == [("wato_folder", "Folder")]


def test_the_page_names_a_filter_once() -> None:
    request = _request([("unapplied", "wato_folder,wato_folder")])

    assert read_unapplied_filter_titles(request, _TITLES.get) == [("wato_folder", "Folder")]


def test_a_page_opened_without_the_variable_names_no_filter() -> None:
    assert read_unapplied_filter_titles(_request([]), _TITLES.get) == []


def _url(filter_node: str | None, unapplied: Sequence[FilterName]) -> str:
    return f"page.py?filter={filter_node}&unapplied={','.join(unapplied)}"


# A host name filter that is set, and a folder filter that is not.
_CONTEXT: VisualContext = {"hostregex": {"host_regex": "web"}, "wato_folder": {"wato_folder": ""}}


def test_a_link_carries_the_filters_it_took_over() -> None:
    def translate(_context: VisualContext) -> ContextFilterTranslation[str]:
        return ContextFilterTranslation(filter="name~web", unapplied=["wato_folder"])

    assert (
        build_link_url(_CONTEXT, translate, _url) == "page.py?filter=name~web&unapplied=wato_folder"
    )


def test_a_link_that_cannot_take_over_the_filters_names_every_filter_that_is_set() -> None:
    def translate(_context: VisualContext) -> ContextFilterTranslation[str]:
        raise RuntimeError("translation broke")

    assert build_link_url(_CONTEXT, translate, _url) == "page.py?filter=None&unapplied=hostregex"


def test_a_link_whose_filters_the_page_rejects_names_every_filter_that_is_set() -> None:
    def translate(_context: VisualContext) -> ContextFilterTranslation[str]:
        return ContextFilterTranslation(filter="invalid", unapplied=[])

    def url(filter_node: str | None, unapplied: Sequence[FilterName]) -> str:
        if filter_node == "invalid":
            raise ValueError("does not validate")
        return _url(filter_node, unapplied)

    assert build_link_url(_CONTEXT, translate, url) == "page.py?filter=None&unapplied=hostregex"


def test_a_link_that_cannot_take_over_the_filters_does_not_name_an_ignored_flag() -> None:
    def translate(_context: VisualContext) -> ContextFilterTranslation[str]:
        raise RuntimeError("translation broke")

    context: VisualContext = {**_CONTEXT, "host_acknowledged": {"is_host_acknowledged": "-1"}}

    assert build_link_url(context, translate, _url) == "page.py?filter=None&unapplied=hostregex"


def test_a_page_shows_a_condition_its_columns_show() -> None:
    can_show = build_column_filter_check(frozenset({"name:contains"}))

    assert can_show({"type": "condition", "field": "name", "op": "contains", "value": "web"})


def test_a_page_cannot_show_a_condition_its_columns_do_not_name() -> None:
    can_show = build_column_filter_check(frozenset({"name:contains"}))

    assert not can_show(
        {
            "type": "and",
            "children": [
                {"type": "condition", "field": "name", "op": "contains", "value": "web"},
                {"type": "condition", "field": "alias", "op": "contains", "value": "web"},
            ],
        }
    )


def test_a_page_cannot_show_an_operator_the_column_filter_of_its_field_does_not_show() -> None:
    can_show = build_column_filter_check(frozenset({"last_check:gte", "last_check:lte"}))

    assert not can_show({"type": "condition", "field": "last_check", "op": "gt", "value": 0})


def test_a_page_shows_the_two_bounds_of_a_range_on_one_field() -> None:
    can_show = build_column_filter_check(frozenset({"num_services:gte", "num_services:lte"}))

    assert can_show(
        {
            "type": "and",
            "children": [
                {"type": "condition", "field": "num_services", "op": "gte", "value": 1},
                {"type": "condition", "field": "num_services", "op": "lte", "value": 5},
            ],
        }
    )


def test_a_page_cannot_show_two_conditions_on_one_field_that_are_no_range() -> None:
    can_show = build_column_filter_check(frozenset({"tags:all_of"}))

    assert not can_show(
        {
            "type": "and",
            "children": [
                {"type": "condition", "field": "tags", "op": "all_of", "value": ["prod"]},
                {"type": "condition", "field": "tags", "op": "all_of", "value": ["linux"]},
            ],
        }
    )
