#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import urlencode

from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.monitor.legacy_context import (
    build_column_filter_check,
    encode_unapplied_filters,
    read_unapplied_filter_titles,
)

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
