#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Literal, Tuple, TypedDict, Union

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
    yield from _check_cpu_load_type(
        params.get("levels"),
        section.load.load15,
        "15",
        section.num_cpus,
        _processor_type_info(section.type),
    )

    for level_name, level_value in section.load._asdict().items():
        if level_name == "load15":
            # we already yielded this metric by check_levels or check_levels_predictive.
            continue

        yield Metric(
            level_name,
            level_value,
            # upper bound of load1 is used for displaying cpu count in graph title
            boundaries=(0, section.num_cpus),
        )


def _check_cpu_load_type(
    levels: dict[str, Any] | tuple[float, float] | None,
    value: float,
    avg: Literal["15"],
    num_cpus: int,
    proc_name: str,
) -> CheckResult:
    label = f"{avg} min load"

    if isinstance(levels, dict):
        # predictive levels
        yield from check_levels_predictive(
            value,
            levels=levels,
            metric_name=f"load{avg}",
            label=label,
        )
    else:
        # warning and critical levels are dependent on cpu count;
        # rule defines levels for one cpu.
        levels_upper = (
            (levels[0] * num_cpus, levels[1] * num_cpus) if isinstance(levels, tuple) else None
        )
        yield from check_levels(
            value,
            metric_name=f"load{avg}",
            levels_upper=levels_upper,
            label=label,
        )

    # provide additional info text
    per_core_txt = f"{avg} min load per core: {(value/num_cpus):.2f} ({num_cpus} {proc_name}cores)"
    yield Result(state=State.OK, summary=per_core_txt)
