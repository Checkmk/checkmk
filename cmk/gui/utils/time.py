#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

import time


# TODO: move this to a new valuespec DateAndTimePicker
#       see https://jira.lan.tribe29.com/browse/CMK-15343
def timezone_utc_offset_str(timestamp: float | None = None) -> str:
    local_time = time.localtime() if timestamp is None else time.localtime(timestamp)
    return (
        "[UTC"
        + ("+" if local_time.tm_gmtoff >= 0 else "-")
        + time.strftime("%H:%M", time.gmtime(abs(local_time.tm_gmtoff)))
        + "]"
    )
