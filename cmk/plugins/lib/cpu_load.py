#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import check_levels_predictive
from cmk.agent_based.v2 import CheckResult, Result, State

from .cpu import ProcessorType, Section


class CPULoadParams(TypedDict):
    levels1: None | tuple[float, float] | dict[str, Any]
    levels5: None | tuple[float, float] | dict[str, Any]
    levels15: None | tuple[float, float] | dict[str, Any]


def _processor_type_info(proc_type: ProcessorType) -> str:
    """
    >>> _processor_type_info(ProcessorType.unspecified)
    ''
    >>> _processor_type_info(ProcessorType.logical)
    'logical '
    """
    return "" if proc_type is ProcessorType.unspecified else f"{proc_type.name} "


def check_cpu_load(params: CPULoadParams, section: Section) -> CheckResult:
    proc_info = _processor_type_info(section.type)
    yield from _check_cpu_load_type(
        params["levels15"],
        section.load.load15,
        "15",
        section.num_cpus,
        proc_info,
        notice_only=False,
    )

    yield from _check_cpu_load_type(
        params["levels1"],
        section.load.load1,
        "1",
        section.num_cpus,
        proc_info,
        notice_only=True,
    )

    yield from _check_cpu_load_type(
        params["levels5"],
        section.load.load5,
        "5",
        section.num_cpus,
        proc_info,
        notice_only=True,
    )


def _check_cpu_load_type(
    levels: dict[str, Any] | tuple[float, float] | None,
    value: float,
    avg: Literal["1", "5", "15"],
    num_cpus: int,
    proc_name: str,
    *,
    notice_only: bool,
) -> CheckResult:
    label = f"{avg} min load"

    if isinstance(levels, dict):
        # predictive levels
        for e in check_levels_predictive(
            value,
            levels=levels,
            metric_name=f"load{avg}",
            label=label,
            boundaries=(0, num_cpus) if avg == "1" else None,
        ):
            yield (
                Result(state=e.state, notice=e.details)
                if notice_only and isinstance(e, Result)
                else e
            )
    else:
        # warning and critical levels are dependent on cpu count;
        # rule defines levels for one cpu.
        levels_upper = (
            (levels[0] * num_cpus, levels[1] * num_cpus) if isinstance(levels, tuple) else None
        )
        yield from check_levels_v1(
            value,
            metric_name=f"load{avg}",
            levels_upper=levels_upper,
            label=label,
            notice_only=notice_only,
            boundaries=(0, num_cpus) if avg == "1" else None,
        )

    # provide additional info text
    per_core_txt = (
        f"{avg} min load per core: {(value / num_cpus):.2f} ({num_cpus} {proc_name}cores)"
    )
    yield (
        Result(state=State.OK, notice=per_core_txt)
        if notice_only
        else Result(state=State.OK, summary=per_core_txt)
    )
