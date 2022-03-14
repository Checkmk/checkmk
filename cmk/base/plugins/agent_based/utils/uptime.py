#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Mapping, NamedTuple, Optional

from ..agent_based_api.v1 import check_levels, render, Result, Service, State
from ..agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


class Section(NamedTuple):
    uptime_sec: Optional[float]
    message: Optional[str]


def discover(section: Section) -> DiscoveryResult:
    if section.uptime_sec:
        yield Service()


def check(params: Mapping[str, Any], section: Section) -> CheckResult:

    if section.message:
        yield Result(state=State.UNKNOWN, summary=section.message)

    if section.uptime_sec is None:
        return

    up_date = render.datetime(time.time() - section.uptime_sec)
    yield Result(state=State.OK, summary=f"Up since {up_date}")

    yield from check_levels(
        section.uptime_sec,
        levels_upper=params.get("max"),
        levels_lower=params.get("min"),
        metric_name="uptime",
        render_func=render.timespan,
        label="Uptime",
    )
