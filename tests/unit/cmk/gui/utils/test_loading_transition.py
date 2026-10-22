#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.loading_transition import (
    loading_transition,
    loading_transition_onclick,
    LoadingTransition,
    with_loading_transition,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.web.utils.html import HTML
from tests.unit.cmk.gui.compare_html import click_handling


def test_onclick_hands_the_click_event_to_the_transition() -> None:
    assert loading_transition_onclick(LoadingTransition.table) == (
        "cmk.utils.makeLoadingTransition('table', 1000, undefined, event);"
    )


def test_onclick_quotes_the_title_as_a_javascript_string() -> None:
    assert loading_transition_onclick(LoadingTransition.table, title="Host's parameters") == (
        """cmk.utils.makeLoadingTransition('table', 1000, "Host's parameters", event);"""
    )


def test_with_loading_transition_shows_the_transition_by_click_action() -> None:
    code = with_loading_transition(HTML.without_escaping('<a href="view.py">All</a>'), None)

    assert click_handling(code, "span") == (
        None,
        "loading_transition",
        {"template": "", "delay_ms": "1000"},
    )


@pytest.mark.usefixtures("request_context")
def test_loading_transition_shows_the_transition_by_click_action() -> None:
    with output_funnel.plugged():
        with loading_transition(LoadingTransition.table, delay_ms=500, title="Hosts"):
            output_funnel.write(b'<a href="view.py">All</a>')
        code = output_funnel.drain()

    assert click_handling(code, "span") == (
        None,
        "loading_transition",
        {"template": "table", "delay_ms": "500", "title": "Hosts"},
    )
