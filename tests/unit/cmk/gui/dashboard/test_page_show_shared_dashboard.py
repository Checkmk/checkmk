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
