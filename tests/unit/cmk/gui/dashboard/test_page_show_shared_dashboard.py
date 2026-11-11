#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import replace

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard import get_all_dashboards
from cmk.gui.dashboard.page_show_shared_dashboard import (
    compute_widget_titles,
    SharedDashboardPageComponents,
)
from cmk.gui.dashboard.type_defs import DashboardConfig
from cmk.gui.type_defs import GraphTimerange
from cmk.gui.utils.graph_refresh import GRAPH_REFRESH_INTERVALS_SECONDS
from cmk.shared_typing.global_time_picker import CustomGraphTimeRange
from cmk.web.utils.request_cache import RequestCache


def test_the_shared_page_carries_the_site_default_time_range(load_config: Config) -> None:
    config = replace(
        load_config,
        graph_timeranges=[
            GraphTimerange(title="The last 2 hours", duration=7200),
            GraphTimerange(title="The last day", duration=86400),
        ],
    )

    assert SharedDashboardPageComponents.default_time_range(config) == 7200


def test_the_shared_time_picker_offers_the_site_graph_time_ranges(load_config: Config) -> None:
    config = replace(
        load_config,
        graph_timeranges=[
            GraphTimerange(title="The last 2 hours", duration=7200),
            GraphTimerange(title="The last day", duration=86400),
        ],
    )

    time_picker = SharedDashboardPageComponents.global_time_picker(config)

    assert time_picker.custom_time_ranges == [
        CustomGraphTimeRange(title="The last 2 hours", total_seconds=7200),
        CustomGraphTimeRange(title="The last day", total_seconds=86400),
    ]
    assert time_picker.default_time_range == 7200


def test_the_shared_time_picker_leaves_the_start_of_week_to_the_browser(
    load_config: Config,
) -> None:
    assert SharedDashboardPageComponents.global_time_picker(load_config).first_day_of_week is None


def test_the_shared_refresh_control_starts_live_with_the_frontend_default_interval(
    load_config: Config,
) -> None:
    refresh = SharedDashboardPageComponents.global_time_picker(load_config).refresh

    assert refresh.starts_live
    assert refresh.interval_seconds is None
    assert refresh.interval_choices_seconds == list(GRAPH_REFRESH_INTERVALS_SECONDS)


def test_widget_titles_skip_a_widget_of_an_unknown_type(load_config: Config) -> None:
    builtin = next(
        board for (owner, _name), board in get_all_dashboards().items() if owner == UserId.builtin()
    )
    board: DashboardConfig = {
        **builtin,
        "widgets": {
            "unknown": {"type": "notification_analysis", "position": (1, 1), "size": (10, 10)}
        },
    }

    assert compute_widget_titles(board, RequestCache(load_config)) == {}
