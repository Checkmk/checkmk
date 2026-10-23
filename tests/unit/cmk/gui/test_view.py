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
from cmk.gui.painter import PainterConfig, PainterContext
from cmk.gui.type_defs import SorterSpec, ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views.store import multisite_builtin_views
from cmk.ruleset_matcher.tags import TagConfig, TagGroupID, TagID
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context

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
        make_painter_context(UserPermissions({}, {}, {}, [])),
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


def _painter_context_with_tags(tags: TagConfig) -> PainterContext:
    context = make_painter_context(UserPermissions({}, {}, {}, []))
    return PainterContext(
        config=PainterConfig.from_config(Config(tags=tags)),
        request=context.request,
        painter_options=context.painter_options,
        theme=context.theme,
        url_renderer=context.url_renderer,
        user_permissions=context.user_permissions,
    )


def test_a_view_sorts_by_the_host_tags_of_its_painter_context() -> None:
    spec: ViewSpec = copy.deepcopy(multisite_builtin_views[SELF_RELOADING_VIEW])
    spec["sorters"] = [SorterSpec(sorter="host_tag_whoot", negate=False)]
    tags = TagConfig.from_config(
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": TagGroupID("whoot"),
                    "topic": "Blubberei",
                    "tags": [{"aux_tags": [], "id": TagID("bla"), "title": "Bla"}],
                    "title": "Whoot",
                },
            ],
        }
    )
    view = View(
        SELF_RELOADING_VIEW,
        spec,
        spec.get("context", {}),
        _painter_context_with_tags(tags),
        RequestCache(Config()),
    )
    assert [entry.sorter.ident for entry in view.sorters] == ["host_tag_whoot"]
