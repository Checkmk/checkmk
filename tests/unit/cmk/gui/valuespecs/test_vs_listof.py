#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import json

import pytest

import cmk.gui.valuespec as vs
from tests.unit.cmk.gui.compare_html import click_handling, inline_event_handlers, ts_function_call

from .utils import expect_validate_failure, expect_validate_success, render_input, request_var


def get_list_of(allow_empty: bool = True) -> vs.ListOf:
    return vs.ListOf(
        valuespec=vs.Tuple([vs.Integer(), vs.Password()]),
        allow_empty=allow_empty,
    )


class TestListOf:
    def test_validate(self) -> None:
        expect_validate_success(get_list_of(), [])
        expect_validate_failure(get_list_of(allow_empty=False), [])
        expect_validate_success(get_list_of(), [(1, "1"), (2, "2")])
        expect_validate_failure(get_list_of(), [(1, "1"), (2, 2)])
        expect_validate_failure(get_list_of(), ((1, "1"),))

    def test_canonical_value(self) -> None:
        assert not get_list_of().canonical_value()

    def test_mask(self) -> None:
        assert get_list_of().mask([(1, "pwd")]) == [(1, "******")]

    def test_value_to_json(self) -> None:
        assert get_list_of().value_to_json([(1, "eins"), (2, "zwei")]) == [[1, "eins"], [2, "zwei"]]

    def test_from_json(self) -> None:
        assert get_list_of().value_from_json([[1, "eins"], [2, "zwei"]]) == [
            (1, "eins"),
            (2, "zwei"),
        ]

    @pytest.mark.usefixtures("request_context")
    def test_from_html_vars(self) -> None:
        with request_var(
            l_count="6",
            l_indexof_3="1",
            l_indexof_5="2",
            l_3_0="1",
            l_3_1="eins",
            l_5_0="2",
            l_5_1="zwei",
        ):
            assert get_list_of().from_html_vars("l") == [(1, "eins"), (2, "zwei")]


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_renders_without_inline_event_handlers() -> None:
    list_of = vs.ListOf(valuespec=vs.Integer(), sort_by=0)

    assert inline_event_handlers(render_input(list_of, [1, 2])) == []


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_adds_entries_by_click_action() -> None:
    code = render_input(vs.ListOf(valuespec=vs.Integer()), [1])

    assert click_handling(code, "input#vp_add") == (
        None,
        "valuespec_listof_add",
        {"varprefix": "vp", "magic": "@!@", "style": "regular"},
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_sorts_entries_by_click_action() -> None:
    code = render_input(vs.ListOf(valuespec=vs.Integer(), sort_by=0), [1])

    assert click_handling(code, "input#vp_sort") == (
        None,
        "valuespec_listof_sort",
        {"varprefix": "vp", "magic": "@!@", "sort_by": "0"},
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_entry_is_deleted_by_click_action() -> None:
    code = render_input(vs.ListOf(valuespec=vs.Integer()), [1])

    assert click_handling(code, "#vp_entry_1 a.delete_button") == (
        None,
        "valuespec_listof_delete",
        {"varprefix": "vp"},
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_entry_is_moved_by_element_dragger() -> None:
    code = render_input(vs.ListOf(valuespec=vs.Integer()), [1])

    assert ts_function_call(code, "#vp_entry_1 a.element_dragger") == (
        "element_dragger",
        {
            "dragging_tag": "TR",
            "drop_handler": "listof_drop_handler",
            "drop_handler_arguments": {"varprefix": "vp"},
        },
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_multiple_renders_without_inline_event_handlers() -> None:
    list_of_multiple = vs.ListOfMultiple(
        choices=[("a", vs.Integer(title="A")), ("b", vs.Integer(title="B"))],
        choice_page_name="ajax_choice",
    )

    assert inline_event_handlers(render_input(list_of_multiple, {"a": 1})) == []


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_multiple_adds_choices_by_click_action() -> None:
    list_of_multiple = vs.ListOfMultiple(
        choices=[("a", vs.Integer(title="A"))],
        choice_page_name="ajax_choice",
        page_request_vars={"context": "host"},
    )

    assert click_handling(render_input(list_of_multiple, {}), "input#vp_add") == (
        None,
        "valuespec_listofmultiple_add",
        {
            "varprefix": "vp",
            "choice_page_name": "ajax_choice",
            "page_request_vars": json.dumps({"context": "host"}),
        },
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_list_of_multiple_choice_is_deleted_by_click_action() -> None:
    list_of_multiple = vs.ListOfMultiple(
        choices=[("a", vs.Integer(title="A"))], choice_page_name="ajax_choice"
    )

    assert click_handling(
        render_input(list_of_multiple, {"a": 1}), "#vp_a_row a.delete_button"
    ) == (
        None,
        "valuespec_listofmultiple_delete",
        {"varprefix": "vp", "ident": "a"},
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_label_group_entry_is_deleted_by_click_action() -> None:
    code = render_input(vs.LabelGroup(), [("and", "os:linux")])

    assert click_handling(code, "#vp_entry_1 a.delete_button") == (
        None,
        "valuespec_label_group_delete",
        {
            "varprefix": "vp",
            "first_elem_choices_or_label": json.dumps([["and", "is"], ["not", "is not"]]),
            "show_empty_group_by_default": "true",
        },
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_label_group_renders_without_inline_event_handlers() -> None:
    assert inline_event_handlers(render_input(vs.LabelGroup(), [("and", "os:linux")])) == []
