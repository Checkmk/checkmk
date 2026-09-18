#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.config import Config
from cmk.gui.graphing import (
    default_time_range_seconds,
    global_time_picker_props,
    global_time_picker_refresh,
    user_first_day_of_week,
)
from cmk.shared_typing.global_time_picker import (
    GlobalTimePickerProps,
)


def get_global_time_picker_props(config: Config) -> GlobalTimePickerProps:
    return global_time_picker_props(
        config.graph_timeranges,
        default_time_range_seconds(),
        first_day_of_week=user_first_day_of_week(),
        refresh=global_time_picker_refresh(),
    )
