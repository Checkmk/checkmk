#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import asdict

from tzlocal import get_localzone_name

from cmk.gui.htmllib.html import html
from cmk.gui.type_defs import GraphTimerange
from cmk.shared_typing.global_time_picker import CustomGraphTimeRange, GlobalTimePickerProps


def render_global_time_picker(
    graph_timeranges: Sequence[GraphTimerange],
    default_time_range_seconds: int,
) -> None:
    """Render the global time picker frontend component."""
    props = GlobalTimePickerProps(
        custom_time_ranges=[
            CustomGraphTimeRange(title=timerange["title"], total_seconds=timerange["duration"])
            for timerange in graph_timeranges
        ],
        default_time_range=default_time_range_seconds,
        server_time_zone=get_localzone_name(),
    )
    html.vue_component("cmk-global-time-picker", data=asdict(props))
