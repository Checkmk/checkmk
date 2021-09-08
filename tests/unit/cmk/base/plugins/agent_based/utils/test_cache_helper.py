#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time

import pytest
from freezegun import freeze_time

from cmk.base.plugins.agent_based.utils import cache_helper

from cmk.gui.plugins.views.utils import render_cache_info

NOW_SIMULATED = "2021-06-08 17:02:00.000000"


@pytest.mark.parametrize(
    "cached_at,interval",
    [
        (
            1623171600,
            300,
        )
    ],
)
@freeze_time(NOW_SIMULATED)
def test_gui_vs_base_render_cache_info(cached_at, interval):
    cache_info_gui = render_cache_info(
        "",
        {
            "service_cached_at": cached_at,
            "service_cache_interval": interval,
        },
    )
    age = time.time() - cached_at
    cache_info_base = cache_helper.render_cache_info(
        cache_helper.CacheInfo(
            age=age,
            cache_interval=interval,
        )
    )

    for rendered in (cache_info_gui, cache_info_base):
        assert bool(
            # At the moment, we can only match the structure of the rendered result and not the
            # exact values as gui and base are still using different rendering functions for
            # percent and timespan/age
            re.match(
                r"Cache generated *(.*), cache interval: *(.*), elapsed cache lifespan: *(.*)",
                rendered,
            )
        )
