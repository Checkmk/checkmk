#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.config import Config
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.visuals import show_filter_form
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.compare_html import click_handling, inline_event_handlers, ts_function_call


def _filter_form() -> str:
    with output_funnel.plugged():
        show_filter_form(
            info_list=["host"],
            context={"hostregex": {"host_regex": "web"}},
            page_name="allhosts",
            reset_ajax_page="ajax_initial_view_filters",
            request_cache=RequestCache(Config()),
        )
        return output_funnel.drain()


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_filter_form_registers_its_handlers_without_inline_code() -> None:
    code = _filter_form()

    assert inline_event_handlers(code) == []
    assert ts_function_call(code, "form#form_filter") == ("filter_form_remove_vars_on_submit", {})
    assert click_handling(code, "div.side_popup_controls a.add") == (
        None,
        "page_menu_toggle_popup_filter_list",
        {"filter_list_id": "_popup_filter_list"},
    )


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_filter_form_resets_the_filters_by_click_action() -> None:
    _onclick, action, arguments = click_handling(_filter_form(), "input.reset")

    assert action == "valuespec_visual_filter_list_reset"
    assert isinstance(arguments, dict)
    assert arguments["page_name"] == "allhosts"
    assert arguments["reset_ajax_page"] == "ajax_initial_view_filters"
    assert json.loads(arguments["context"]) == {"hostregex": {"host_regex": "web"}}


@pytest.mark.usefixtures("request_context", "with_user_login", "patch_theme")
def test_filter_form_adds_filters_by_click_action() -> None:
    _onclick, action, arguments = click_handling(_filter_form(), "a#_add_hostregex")

    assert action == "valuespec_listofmultiple_add"
    assert isinstance(arguments, dict)
    assert arguments["varprefix"] == ""
    assert arguments["filter_list_id"] == "_popup_filter_list_selected"
