#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Final

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)

CheckpointInfo = dict[str, str]
Section = dict[str, list[CheckpointInfo]]

SECONDS_PER_DAY: Final[int] = 86400

Levels = NoLevelsT | FixedLevelsT[float]

NO_LEVELS: NoLevelsT = ("no_levels", None)

CheckpointParams = Mapping[str, Levels]

hyperv_vm_checkpoints_default_params: CheckpointParams = {
    "age_oldest": ("fixed", (10 * SECONDS_PER_DAY, 20 * SECONDS_PER_DAY)),
    "age": NO_LEVELS,
}


def parse_hyperv_vm_checkpoints(string_table: StringTable) -> dict[str, list[CheckpointInfo]]:
    parsed: dict[str, list[CheckpointInfo]] = {}

    if not string_table:
        return parsed

    checkpoints: list[CheckpointInfo] = []
    current_checkpoint: CheckpointInfo = {}

    for line in string_table:
        if not line:
            continue

        match line:
            case ["checkpoint.name", *name_parts]:
                if current_checkpoint:
                    checkpoints.append(current_checkpoint)
                current_checkpoint = {"name": " ".join(name_parts)}
            case ["checkpoint.path", *path_parts]:
                current_checkpoint["path"] = " ".join(path_parts)
            case ["checkpoint.created", *created_parts]:
                current_checkpoint["created"] = " ".join(created_parts)
            case ["checkpoint.parent", *parent_parts]:
                current_checkpoint["parent"] = " ".join(parent_parts) if parent_parts else ""
            case _:
                pass

    if current_checkpoint:
        checkpoints.append(current_checkpoint)

    parsed["checkpoints"] = checkpoints
    return parsed


def discover_hyperv_vm_checkpoints(section: Section) -> DiscoveryResult:
    if "checkpoints" in section:
        yield Service()


def _parse_checkpoint_ages(checkpoints: Sequence[CheckpointInfo]) -> list[tuple[str, float]]:
    checkpoint_data: list[tuple[str, float]] = []
    current_time: float = time.time()

    # Common date formats from different locales
    date_formats = [
        "%m/%d/%Y %H:%M:%S",  # US format: 07/18/2025 13:44:18
        "%d/%m/%Y %H:%M:%S",  # European format: 18/07/2025 13:44:18
        "%Y-%m-%d %H:%M:%S",  # ISO format: 2025-07-18 13:44:18
        "%d.%m.%Y %H:%M:%S",  # German format: 18.07.2025 13:44:18
        "%Y/%m/%d %H:%M:%S",  # Asian format: 2025/07/18 13:44:18
        "%m-%d-%Y %H:%M:%S",  # US with dashes: 07-18-2025 13:44:18
        "%d-%m-%Y %H:%M:%S",  # European with dashes: 18-07-2025 13:44:18
        "%m/%d/%Y %I:%M:%S %p",  # US with AM/PM: 07/18/2025 1:44:18 PM
        "%d/%m/%Y %I:%M:%S %p",  # European with AM/PM: 18/07/2025 1:44:18 PM
        "%m/%d/%y %H:%M:%S",  # US 2-digit year: 07/18/25 13:44:18
        "%d/%m/%y %H:%M:%S",  # European 2-digit year: 18/07/25 13:44:18
    ]

    for checkpoint in checkpoints:
        if "created" not in checkpoint or not checkpoint["created"]:
            continue

        created_str = checkpoint["created"].strip()
        parsed_successfully = False

        for date_format in date_formats:
            try:
                checkpoint_time = time.strptime(created_str, date_format)
                checkpoint_timestamp = time.mktime(checkpoint_time)
                age_seconds = current_time - checkpoint_timestamp
                checkpoint_data.append((checkpoint["name"], age_seconds))
                parsed_successfully = True
                break
            except (ValueError, OverflowError):
                continue

        if not parsed_successfully:
            continue

    return checkpoint_data


def check_hyperv_vm_checkpoints(params: CheckpointParams, section: Section) -> CheckResult:
    if "checkpoints" not in section:
        yield Result(state=State.UNKNOWN, summary="No checkpoint data found")
        return

    checkpoints = section["checkpoints"]
    if not checkpoints:
        yield Result(state=State.OK, summary="Checkpoints: 0")
        return

    checkpoint_data = _parse_checkpoint_ages(checkpoints)

    if not checkpoint_data:
        yield Result(state=State.UNKNOWN, summary="No valid checkpoint dates found")
        return

    checkpoint_data.sort(key=lambda x: x[1])

    yield Result(state=State.OK, summary=f"Checkpoints: {len(checkpoint_data)}")

    newest_checkpoint = checkpoint_data[0]
    oldest_checkpoint = max(checkpoint_data, key=lambda x: x[1])

    newest_name, newest_age = newest_checkpoint
    oldest_name, oldest_age = oldest_checkpoint

    age_levels = params.get("age", hyperv_vm_checkpoints_default_params["age"])
    yield from check_levels(
        newest_age,
        metric_name="age",
        levels_upper=age_levels,
        render_func=render.timespan,
        label=f"Last ({newest_name})",
    )

    age_oldest_levels = params.get("age_oldest", hyperv_vm_checkpoints_default_params["age_oldest"])
    yield from check_levels(
        oldest_age,
        metric_name="age_oldest",
        levels_upper=age_oldest_levels,
        render_func=render.timespan,
        label=f"Oldest ({oldest_name})",
    )


agent_section_hyperv_vm_checkpoints = AgentSection(
    name="hyperv_vm_checkpoints",
    parse_function=parse_hyperv_vm_checkpoints,
)

check_plugin_hyperv_vm_checkpoints = CheckPlugin(
    name="hyperv_vm_checkpoints",
    sections=["hyperv_vm_checkpoints"],
    service_name="Hyper-V VM Checkpoints",
    discovery_function=discover_hyperv_vm_checkpoints,
    check_function=check_hyperv_vm_checkpoints,
    check_default_parameters=hyperv_vm_checkpoints_default_params,
    check_ruleset_name="hyperv_vm_checkpoints",
)
