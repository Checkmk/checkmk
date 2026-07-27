#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry

_TEMPLATE_SPEC = {
    "graph_type": "template",
    "site": "NO_SITE",
    "host_name": "my-host",
    "service_description": "CPU load",
    "graph_id": "cpu_load",
}


_EMPTY_DASHBOARD = {
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


def test_add_to_visual_stores_the_graph_in_the_dashboard(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    # mock_livestatus is required because graph widgets want the connected site PIDs; no queries
    # are actually executed.
    clients.DashboardClient.create_relative_grid_dashboard(payload=_EMPTY_DASHBOARD)

    clients.Graph.add_to_visual(
        specification=_TEMPLATE_SPEC, family="dashboards", target_id="my_dashboard"
    )

    widgets = clients.DashboardClient.get_relative_grid_dashboard("my_dashboard").json[
        "extensions"
    ]["widgets"]
    [widget] = list(widgets.values())
    # The stored widget replays the specification, addressed to the host the spec named.
    assert "my-host" in str(widget)


def test_add_to_visual_rejects_views(clients: ClientRegistry) -> None:
    # Views are a registered visual type, but their add handler is a no-op: accepting them would
    # report success while storing nothing.
    resp = clients.Graph.add_to_visual(
        specification=_TEMPLATE_SPEC,
        family="views",
        target_id="allhosts",
        expect_ok=False,
    )

    assert resp.status_code == 400
    assert "views" in resp.json["detail"]


def test_add_to_visual_rejects_an_unknown_visual_type(clients: ClientRegistry) -> None:
    resp = clients.Graph.add_to_visual(
        specification=_TEMPLATE_SPEC,
        family="does_not_exist",
        target_id="my_dashboard",
        expect_ok=False,
    )

    assert resp.status_code == 400
    assert "does_not_exist" in resp.json["detail"]


def test_add_to_container_rejects_an_unknown_container_type(clients: ClientRegistry) -> None:
    resp = clients.Graph.add_to_container(
        specification=_TEMPLATE_SPEC,
        family="does_not_exist",
        target_id="my_graph_collection",
        expect_ok=False,
    )

    assert resp.status_code == 400
    assert "does_not_exist" in resp.json["detail"]


def test_add_to_visual_rejects_an_unparseable_specification(clients: ClientRegistry) -> None:
    resp = clients.Graph.add_to_visual(
        specification={"graph_type": "not_a_graph_type"},
        family="dashboards",
        target_id="my_dashboard",
        expect_ok=False,
    )

    assert resp.status_code == 400
    assert "specification" in resp.json["detail"]


def test_add_to_visual_rejects_a_graph_kind_without_an_add_to_action(
    clients: ClientRegistry,
) -> None:
    # An explicit graph carries its metrics inline and declares no add_visual_type, so there is
    # nothing the backends could store and replay.
    resp = clients.Graph.add_to_visual(
        specification={"graph_type": "explicit", "metrics": [], "specification": []},
        family="dashboards",
        target_id="my_dashboard",
        expect_ok=False,
    )

    assert resp.status_code == 400


def test_add_to_visual_unknown_target_is_404(clients: ClientRegistry) -> None:
    resp = clients.Graph.add_to_visual(
        specification=_TEMPLATE_SPEC,
        family="dashboards",
        target_id="does_not_exist",
        expect_ok=False,
    )

    assert resp.status_code == 404
