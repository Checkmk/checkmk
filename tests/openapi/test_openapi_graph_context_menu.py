#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.rest_api_client import ClientRegistry

_DASHBOARD = {
    "id": "my_dashboard",
    "general_settings": {
        "title": {"text": "Test Dashboard", "render": True, "include_context": False},
        "description": "A dashboard to add a graph to",
        "menu": {
            "topic": "overview",
            "sort_index": 99,
            "search_terms": [],
            "is_show_more": False,
        },
        "visibility": {
            "hide_in_monitor_menu": False,
            "hide_in_drop_down_menus": False,
            "share": "no",
        },
    },
    "filter_context": {
        "restricted_to_single": [],
        "filters": {},
        "mandatory_context_filters": [],
    },
    "widgets": {},
    "layout": {"type": "relative_grid"},
}


def test_fetch_context_menu_offers_the_users_own_dashboard(clients: ClientRegistry) -> None:
    # Building the menu checks general.edit_dashboards, which the endpoint has to declare.
    assert clients.Graph.fetch_context_menu("pnpgraph").json["value"] == []

    clients.DashboardClient.create_relative_grid_dashboard(payload=_DASHBOARD)

    [group] = clients.Graph.fetch_context_menu("pnpgraph").json["value"]
    assert group["heading"] == "Add to dashboard"
    [item] = group["items"]
    assert item["action"] == {"id": "add_to_visual", "parameters": ["dashboards", "my_dashboard"]}
