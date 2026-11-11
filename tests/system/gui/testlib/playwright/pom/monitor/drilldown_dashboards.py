#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The widgets and runtime filters of the dashboards to drill down from and into."""

import re
from collections.abc import Mapping, Sequence
from typing import Final
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import BaseDashboard

# The service and metric every Linux and Windows test host reports.
CPU_SERVICE: Final = "CPU utilization"
_CPU_METRIC: Final = "util"

_WIDGET_SIZE: Final = {"width": 40, "height": 20}

_HOST_NAME_FILTER: Final = "Host name (regex)"
_SERVICE_NAME_FILTER: Final = "Service name (regex)"


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


def apply_host_name_runtime_filter(dashboard: BaseDashboard, host_name: str) -> str:
    """Narrow the dashboard to the host by the 'Host name (regex)' runtime filter.

    Returns the filter's value in the dashboard URL, the picked name as a regex.
    """
    return _apply_name_runtime_filter(dashboard, _HOST_NAME_FILTER, host_name, "host_regex")


def apply_service_name_runtime_filter(dashboard: BaseDashboard, service_name: str) -> str:
    """Narrow the dashboard to the service by the 'Service name (regex)' runtime filter.

    Returns the filter's value in the dashboard URL, the picked name as a regex.
    """
    return _apply_name_runtime_filter(
        dashboard, _SERVICE_NAME_FILTER, service_name, "service_regex"
    )


def _apply_name_runtime_filter(
    dashboard: BaseDashboard, filter_name: str, name: str, variable: str
) -> str:
    # The filter offers the site's names to pick from.
    sidebar = dashboard.open_runtime_filters()
    sidebar.add_filter_to_host_selection(filter_name)
    sidebar.get_filter_combobox(filter_name).click()
    sidebar.dropdown_list_filter_textbox.fill(name)
    sidebar.locator().get_by_role("option", name=name, exact=True).click()
    sidebar.apply_button.click()
    expect(dashboard.page, "The runtime filter did not reach the dashboard URL").to_have_url(
        re.compile(rf"[?&]{variable}=")
    )
    return url_variables(dashboard.page.url)[variable]


def url_variables(url: str) -> dict[str, str]:
    """The query variables of the URL, each with its first value."""
    return {name: values[0] for name, values in parse_qs(urlparse(url).query).items()}
