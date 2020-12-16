#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import set_item_state, get_item_state
from cmk.base.check_api import check_levels
from typing import (  #
    Generator, Optional, Tuple,
)
import time

from cmk.base.plugins.agent_based.agent_based_api.v1 import (  #
    render,)


# ==================================================================================================
# DEPRECATED WARNING
# tolerance_check HERE HAS ALREADY BEEN MIGRATED TO THE NEW CHECK API.
# PLEASE DO NOT MODIFY THIS FUNCTION ANYMORE. INSTEAD, MODIFY THE MIGRATED CODE
# RESIDING IN
# cmk/base/plugins/agent_based/utils/timesync.py
# ==================================================================================================
def tolerance_check(
    *,
    set_sync_time: Optional[float],
    levels: Optional[Tuple[float, float]],
    notice_only: bool = False,
) -> Generator[Tuple[int, str], None, None]:
    if set_sync_time is not None:
        set_item_state("time_server", set_sync_time)
        return

    last_sync = get_item_state("time_server")
    now = time.time()
    pot_newline = "\n" if notice_only else ""
    label = "Time since last sync"

    if last_sync is None:
        set_item_state("time_server", now)
        yield 0, f"{pot_newline}{label}: N/A (started monitoring)"
        return

    state, text, _metric = check_levels(
        now - last_sync,
        None,
        levels,
        human_readable_func=render.timespan,
        infoname=label,
    )
    yield state, text if state else f"{pot_newline}{text}"
