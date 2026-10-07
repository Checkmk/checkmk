#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

import pytest

from cmk.gui.config import Config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views.store import multisite_builtin_views
from cmk.web.utils.request_cache import RequestCache

# A builtin view without engine graphs, which reloads on its own interval.
SELF_RELOADING_VIEW = "allhosts"


def _view(*, allow_browser_reload: bool) -> View:
    request.set_var("display_options", "R")
    display_options.load_from_html(request, html)
    spec: ViewSpec = copy.deepcopy(multisite_builtin_views[SELF_RELOADING_VIEW])
    view = View(
        SELF_RELOADING_VIEW,
        spec,
        spec.get("context", {}),
        UserPermissions({}, {}, {}, []),
        RequestCache(Config()),
    )
    view.allow_browser_reload = allow_browser_reload
    # Guards the premise: a view that never reloads would make the assertions below vacuous.
    assert spec["browser_reload"] > 0
    assert not view.renders_engine_graphs
    return view


@pytest.mark.usefixtures("request_context")
def test_a_view_reloads_itself() -> None:
    assert _view(allow_browser_reload=True).reloads_itself


@pytest.mark.usefixtures("request_context")
def test_a_view_without_the_browser_reload_does_not_reload_itself() -> None:
    assert not _view(allow_browser_reload=False).reloads_itself
