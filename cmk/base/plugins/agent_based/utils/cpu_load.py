#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Tuple, TypedDict, Union

from ..agent_based_api.v1 import check_levels, check_levels_predictive, Metric, Result, State
from ..agent_based_api.v1.type_defs import CheckResult
from .cpu import ProcessorType, Section


class CPULoadParams(TypedDict, total=False):
    levels: Union[None, Tuple[float, float], Dict[str, Any]]


def _processor_type_info(proc_type: ProcessorType) -> str:
    """
    >>> _processor_type_info(ProcessorType.unspecified)
    ''
    >>> _processor_type_info(ProcessorType.logical)
    'logical '
    """
    return "" if proc_type is ProcessorType.unspecified else f"{proc_type.name} "


def check_cpu_load(params: CPULoadParams, section: Section) -> CheckResult:
    levels = params.get("levels")
    num_cpus = section.num_cpus
    label = "15 min load"

    if isinstance(levels, dict):
        # predictive levels
        yield from check_levels_predictive(
            section.load.load15,
            levels=levels,
            metric_name="load15",
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
            metric_name="load15",
            levels_upper=levels_upper,
            label=label,
        )

    # provide additional info text
    yield Result(
        state=State.OK,
        summary=f"15 min load per core: {(section.load.load15/num_cpus):.2f} "
        f"({num_cpus} {_processor_type_info(section.type)}cores)",
    )

    for level_name, level_value in section.load._asdict().items():
        if level_name == "load15":
            # we already yielded this metric by check_levels or check_levels_predictive.
            continue

        yield Metric(
            level_name,
            level_value,
            # upper bound of load1 is used for displaying cpu count in graph title
            boundaries=(0, num_cpus),
        )
