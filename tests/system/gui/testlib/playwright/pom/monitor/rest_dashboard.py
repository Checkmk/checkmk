#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dashboards built through the REST API, for tests that are not about the wizard.

Every dashboard is shared with all users: on the cloud edition the browser does not log in as
`ADMIN_USER`, who owns them.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from playwright.sync_api import Page

from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.system.site import ADMIN_USER, Site


@contextmanager
def rest_dashboard(
    test_site: Site,
    *,
    dashboard_id: str,
    title: str,
    widgets: Mapping[str, Mapping[str, object]],
    filters: Mapping[str, object] | None = None,
) -> Iterator[None]:
    """A dashboard of the widgets and dashboard filters, deleted again afterwards."""
    payload = {
        "id": dashboard_id,
        "general_settings": {
            "title": {"text": title, "render": True, "include_context": False},
            "description": "",
            "menu": {
                "topic": "overview",
                "sort_index": 99,
                "search_terms": [],
                "is_show_more": False,
            },
            "visibility": {
                "hide_in_monitor_menu": False,
                "hide_in_drop_down_menus": False,
                "share": {"type": "with_all_users"},
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": dict(filters or {}),
            "mandatory_context_filters": [],
        },
        "widgets": {widget_id: dict(widget) for widget_id, widget in widgets.items()},
        "layout": {"type": "relative_grid"},
    }
    with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
        test_site.openapi.dashboard.create_relative_grid_dashboard(payload)
    try:
        yield
    finally:
        if is_cleanup_enabled():
            with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
                test_site.openapi.dashboard.delete(dashboard_id)


def open_dashboard(page: Page, test_site: Site, dashboard_id: str, title: str) -> CustomDashboard:
    """Open the dashboard in the browser, as a page of its own."""
    page.goto(
        test_site.internal_url + f"dashboard.py?name={dashboard_id}&owner={ADMIN_USER}",
        wait_until="load",
    )
    return CustomDashboard(page, page_title=title, navigate_to_page=False)
