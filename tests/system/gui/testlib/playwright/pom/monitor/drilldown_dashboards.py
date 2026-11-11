#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dashboards to drill down from and into, built through the REST API.

The wizard is not what the drill-down tests are about, so they set up their dashboards here.
Every dashboard is shared with all users: on the cloud edition the browser does not log in as
`ADMIN_USER`, who owns them.
"""

import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Final
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, Page

from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import BaseDashboard
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.system.site import ADMIN_USER, Site

# The service and metric every Linux and Windows test host reports.
CPU_SERVICE: Final = "CPU utilization"
_CPU_METRIC: Final = "util"

_WIDGET_SIZE: Final = {"width": 40, "height": 20}

_HOST_NAME_FILTER: Final = "Host name (regex)"


def inherited_link(location_type: str, name: str) -> dict[str, object]:
    """A link to one visual, carrying the widget's filters and the clicked element."""
    return {
        "type": "inherited",
        "location": {"type": location_type, "name": name},
        "include_context": True,
        "include_time_range": False,
        "show_filter_form": False,
    }


def custom_link(
    title: str, location_type: str, name: str, filters: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    """A custom link with one destination, carrying only the given filters of the clicked
    element."""
    return {
        "type": "custom",
        "links": [
            {
                "title": title,
                "location": {"type": location_type, "name": name},
                "filters": [dict(context_filter) for context_filter in filters],
                "include_context": False,
                "include_time_range": False,
                "show_filter_form": False,
            }
        ],
    }


def cpu_top_list(
    title: str,
    contextual_link: Mapping[str, object],
    filters: Mapping[str, object] | None = None,
    y: int = 1,
) -> dict[str, object]:
    """A top list of the hosts' CPU utilization, linking as `contextual_link` says."""
    return {
        "general_settings": {
            "title": {"text": title, "render_mode": "with_background"},
            "render_background": True,
        },
        "content": {
            "type": "top_list",
            "metric": _CPU_METRIC,
            "columns": {"show_service_description": False, "show_bar_visualization": False},
            "display_range": "automatic",
            "ranking_order": "high",
            "limit_to": 10,
            "contextual_link": dict(contextual_link),
        },
        "filters": {"service": {"service": CPU_SERVICE}, **(filters or {})},
        "layout": {
            "type": "relative_grid",
            "position": {"x": 1, "y": y},
            "size": _WIDGET_SIZE,
        },
    }


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


def apply_host_name_runtime_filter(dashboard: BaseDashboard, host_name: str) -> str:
    """Narrow the dashboard to the host by the 'Host name (regex)' runtime filter, which
    offers the site's host names to pick from.

    Returns the filter's value in the dashboard URL, the picked name as a regex.
    """
    sidebar = dashboard.open_runtime_filters()
    sidebar.add_filter_to_host_selection(_HOST_NAME_FILTER, "Host name")
    sidebar.get_filter_combobox(_HOST_NAME_FILTER).click()
    sidebar.dropdown_list_filter_textbox.fill(host_name)
    sidebar.locator().get_by_role("option", name=host_name, exact=True).click()
    sidebar.apply_button.click()
    expect(dashboard.page, "The runtime filter did not reach the dashboard URL").to_have_url(
        re.compile(r"[?&]host_regex=")
    )
    return url_variables(dashboard.page.url)["host_regex"]


def url_variables(url: str) -> dict[str, str]:
    """The query variables of the URL, each with its first value."""
    return {name: values[0] for name, values in parse_qs(urlparse(url).query).items()}


def open_dashboard(page: Page, test_site: Site, dashboard_id: str, title: str) -> CustomDashboard:
    """Open the dashboard in the browser, as a page of its own."""
    page.goto(
        test_site.internal_url + f"dashboard.py?name={dashboard_id}&owner={ADMIN_USER}",
        wait_until="load",
    )
    return CustomDashboard(page, page_title=title, navigate_to_page=False)
