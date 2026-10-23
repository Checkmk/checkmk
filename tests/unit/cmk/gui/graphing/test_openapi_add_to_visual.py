#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.unit.rest_api_client import ClientRegistry


def test_add_to_visual_dashboard_returns_dashboard_redirect_url(clients: ClientRegistry) -> None:
    # CMK-38529: adding a graph to a dashboard has to hand the frontend somewhere to navigate to,
    # the way the legacy "Add to dashboard" popup always did.
    clients.DashboardClient.create_relative_grid_dashboard(
        {
            "id": "test_dashboard",
            "general_settings": {
                "title": {"text": "Test Dashboard", "render": True, "include_context": False},
                "description": "This is a test dashboard",
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
    )

    resp = clients.Graph.add_to_visual(
        specification={
            "graph_type": "template",
            "site": None,
            "host_name": "my-host",
            "service_description": "CPU load",
            "graph_id": "cpu_load",
        },
        family="dashboards",
        target_id="test_dashboard",
    )

    assert resp.json["redirect_url"] == "dashboard.py?name=test_dashboard"
