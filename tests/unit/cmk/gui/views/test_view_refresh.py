#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What a view that paints engine graphs tells the global time picker about refreshing it."""

import copy
import html
import json
import re
from collections.abc import Mapping

import pytest

from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.view_renderer import GUIViewRenderer
from cmk.gui.views.store import multisite_builtin_views

# The builtin view that paints engine graphs, and auto-refreshed long before the picker existed.
ENGINE_GRAPH_VIEW = "service"


def _view(browser_reload: int) -> View:
    spec: ViewSpec = copy.deepcopy(multisite_builtin_views[ENGINE_GRAPH_VIEW])
    spec["browser_reload"] = browser_reload
    view = View(ENGINE_GRAPH_VIEW, spec, spec.get("context", {}), UserPermissions({}, {}, {}, []))
    # Guards the premise: without engine graphs the assertions below would be vacuous.
    assert view.renders_engine_graphs
    return view


def _rendered_refresh(view: View) -> Mapping[str, object]:
    renderer = GUIViewRenderer(
        view, show_buttons=False, page_menu_dropdowns_callback=lambda *args: None
    )
    with output_funnel.plugged():
        renderer._render_time_picker()
        rendered = output_funnel.drain()

    element = re.search(r'<cmk-global-time-picker data="([^"]*)"', rendered)
    assert element is not None, rendered
    refresh: Mapping[str, object] = json.loads(html.unescape(element.group(1)))["refresh"]
    return refresh


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_view_that_auto_refreshed_arrives_live_at_its_own_interval() -> None:
    interval_of_the_view = 30
    view = _view(browser_reload=interval_of_the_view)

    refresh = _rendered_refresh(view)

    assert refresh["starts_live"] is True
    assert refresh["interval_seconds"] == interval_of_the_view


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_view_with_the_reload_turned_off_arrives_paused() -> None:
    # 0 is what the view's "Automatic page reload" setting stores for "off".
    view = _view(browser_reload=0)

    refresh = _rendered_refresh(view)

    assert refresh["starts_live"] is False


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_view_refreshes_by_re_fetching_its_server_rendered_rows() -> None:
    view = _view(browser_reload=30)

    refresh = _rendered_refresh(view)

    assert refresh["reloads_page_content"] is True
