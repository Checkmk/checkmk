#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading

import pytest
from flask import Flask

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.html import html
from cmk.gui.wato.pages._html_elements import wato_html_head, wato_html_page


def _render_page(*, heads: int) -> str:
    with html.output_funnel.plugged():
        with wato_html_page(show_body_end=True):
            for _i in range(heads):
                wato_html_head(title="Title", breadcrumb=Breadcrumb())
        return html.output_funnel.drain()


@pytest.mark.usefixtures("request_context", "frontend_vue_manifest", "patch_theme")
def test_page_closes_the_opened_head() -> None:
    assert _render_page(heads=1).endswith("</html>")


@pytest.mark.usefixtures("request_context", "frontend_vue_manifest", "patch_theme")
def test_head_is_rendered_once_per_page() -> None:
    assert _render_page(heads=2).count('<div class="wato">') == 1


@pytest.mark.usefixtures("request_context")
def test_page_without_head_renders_nothing() -> None:
    assert _render_page(heads=0) == ""


@pytest.mark.usefixtures("request_context", "frontend_vue_manifest", "patch_theme")
def test_page_is_closed_despite_a_concurrent_page(flask_app: Flask) -> None:
    def other_request() -> None:
        with flask_app.test_request_context("/"):
            flask_app.preprocess_request()
            _render_page(heads=0)

    with html.output_funnel.plugged():
        with wato_html_page(show_body_end=True):
            wato_html_head(title="Title", breadcrumb=Breadcrumb())
            thread = threading.Thread(target=other_request)
            thread.start()
            thread.join()
        output = html.output_funnel.drain()

    assert output.endswith("</html>")
