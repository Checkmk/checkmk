#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from html.parser import HTMLParser
from typing import override

import pytest

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.top_heading import requested_drill_up, top_heading
from cmk.shared_typing.drill_up_button import DrillUpButton


class _VueComponentData(HTMLParser):
    """Collects the payload each ``cmk-...`` web component was handed, by component name."""

    def __init__(self) -> None:
        super().__init__()
        self.payloads: dict[str, dict[str, object]] = {}

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not tag.startswith("cmk-"):
            return
        for name, value in attrs:
            if name == "data" and value is not None:
                self.payloads[tag] = json.loads(value)


def _rendered_heading(drill_up: DrillUpButton | None) -> str:
    with html.output_funnel.plugged():
        top_heading(
            html,
            request,
            "All hosts",
            Breadcrumb(),
            browser_reload=0,
            debug=False,
            hide_suggestions=True,
            user_role_ids=[],
            drill_up=drill_up,
        )
        return html.output_funnel.drain()


def _drill_up_payload(rendered: str) -> dict[str, object] | None:
    parser = _VueComponentData()
    parser.feed(rendered)
    return parser.payloads.get("cmk-drill-up-button")


@pytest.mark.usefixtures("request_context")
def test_requested_drill_up_names_the_page_a_drill_down_came_from() -> None:
    request.set_var("_drilled_from", "Main")

    assert requested_drill_up(request) == DrillUpButton(title="Main")


@pytest.mark.usefixtures("request_context")
def test_requested_drill_up_is_none_on_a_page_no_drill_down_opened() -> None:
    assert requested_drill_up(request) is None


@pytest.mark.usefixtures("request_context")
def test_top_heading_offers_the_way_back_to_the_named_page() -> None:
    rendered = _rendered_heading(DrillUpButton(title="Main"))

    assert _drill_up_payload(rendered) == {"title": "Main"}


@pytest.mark.usefixtures("request_context")
def test_top_heading_without_a_drill_up_offers_no_way_back() -> None:
    assert _drill_up_payload(_rendered_heading(None)) is None


@pytest.mark.usefixtures("request_context")
def test_top_heading_keeps_markup_in_the_source_title_as_text() -> None:
    rendered = _rendered_heading(DrillUpButton(title="<b>Main</b>"))

    assert "<b>Main</b>" not in rendered
    assert _drill_up_payload(rendered) == {"title": "<b>Main</b>"}
