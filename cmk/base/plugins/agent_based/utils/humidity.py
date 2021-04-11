#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Tuple

from ..agent_based_api.v1 import check_levels, render

from ..agent_based_api.v1.type_defs import CheckResult

HumidityParamType = Mapping[str, Tuple[float, float]]

def check_humidity(humidity: float, params: HumidityParamType) -> CheckResult:
    yield from check_levels(
        humidity,
        metric_name="humidity",
        levels_upper=params.get("levels"),
        levels_lower=params.get("levels_lower"),
        render_func=render.percent,
        boundaries=(0, 100),
    )
