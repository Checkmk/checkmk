#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import replace

from cmk.gui.config import Config
from cmk.gui.dashboard.page_show_shared_dashboard import SharedDashboardPageComponents
from cmk.gui.type_defs import GraphTimerange


def test_the_shared_page_carries_the_site_default_time_range(load_config: Config) -> None:
    config = replace(
        load_config,
        graph_timeranges=[
            GraphTimerange(title="The last 2 hours", duration=7200),
            GraphTimerange(title="The last day", duration=86400),
        ],
    )

    assert SharedDashboardPageComponents.default_time_range(config) == 7200
