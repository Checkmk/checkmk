#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard.page_edit_dashboard import create_dashboard
from cmk.gui.dashboard.type_defs import DashboardConfig, DEFAULT_RESPONSIVE_GRID_LAYOUT_ID
from cmk.gui.type_defs import DashboardEmbeddedViewSpec


def _stored_responsive_dashboard() -> DashboardConfig:
    return {
        "owner": UserId("test_user"),
        "name": "test_dashboard",
        "context": {},
        "single_infos": [],
        "add_context_to_title": True,
        "title": "Test",
        "description": "",
        "topic": "overview",
        "sort_index": 0,
        "is_show_more": False,
        "icon": None,
        "hidden": False,
        "hidebutton": False,
        "public": False,
        "packaged": False,
        "link_from": {},
        "main_menu_search_terms": [],
        "mtime": 0,
        "widgets": {},
        "show_title": True,
        "mandatory_context_filters": [],
        "layout": {
            "type": "responsive_grid",
            "layouts": {
                DEFAULT_RESPONSIVE_GRID_LAYOUT_ID: {"title": "Default", "breakpoints": {"M", "L"}}
            },
        },
        "embedded_views": {"view1": DashboardEmbeddedViewSpec(datasource="hosts")},  # type: ignore[typeddict-item]
    }


@pytest.mark.usefixtures("request_context")
def test_editing_the_properties_keeps_the_layout_and_the_embedded_views() -> None:
    stored = _stored_responsive_dashboard()

    edited = create_dashboard(stored, {})  # type: ignore[typeddict-item]

    assert (edited["layout"], edited["embedded_views"]) == (
        stored["layout"],
        stored["embedded_views"],
    )


@pytest.mark.usefixtures("request_context")
def test_editing_the_properties_keeps_the_sharing_token() -> None:
    stored = _stored_responsive_dashboard()
    stored["public_token_id"] = "token"

    edited = create_dashboard(stored, {})  # type: ignore[typeddict-item]

    assert edited.get("public_token_id") == "token"
