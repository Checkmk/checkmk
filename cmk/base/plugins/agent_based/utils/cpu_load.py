#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from ..agent_based_api.v1 import check_levels, check_levels_predictive, Metric, Result, State
from ..agent_based_api.v1.type_defs import CheckResult
from .cpu import Section


def check_cpu_load(params: Mapping[str, Any], section: Section) -> CheckResult:
    levels = params.get("levels")
    num_cpus = section.num_cpus
    label = "15 min load"

    if isinstance(levels, dict):
        # predictive levels
        yield from check_levels_predictive(
            section.load.load15,
            levels=levels,
            metric_name='load15',
            label=label,
        )
    else:
        # fixed level thresholds
        levels_upper = None
        if isinstance(levels, tuple):
            # warning and critical levels are dependent on cpu count;
            # rule defines levels for one cpu.
            levels_upper = (levels[0] * num_cpus, levels[1] * num_cpus)
        yield from check_levels(
            section.load.load15,
            metric_name='load15',
            levels_upper=levels_upper,
            label=label,
        )

    # provide additional info text
    yield Result(
        state=State.OK,
        summary=f"15 min load per core: {(section.load.load15/num_cpus):.2f} ({num_cpus} cores)")

    for level_name, level_value in section.load._asdict().items():
        if level_name == 'load15':
            # we already yielded this metric by check_levels or check_levels_predictive.
            continue

        yield Metric(
            level_name,
            level_value,
            # upper bound of load1 is used for displaying cpu count in graph title
            boundaries=(0, num_cpus),
        )
