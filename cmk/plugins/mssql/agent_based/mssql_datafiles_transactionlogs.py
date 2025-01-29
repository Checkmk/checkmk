#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping, Sequence
from contextlib import suppress
from typing import Any, Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    RuleSetType,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import BlocksSubsection, InodesSubsection

_ItemKey = tuple[str | None, str, str]


class MSSQLInstanceData(TypedDict):
    unlimited: bool
    max_size: float | None
    allocated_size: float | None
    used_size: float | None
    mountpoint: str


SectionDatafiles = Mapping[_ItemKey, MSSQLInstanceData]


def parse_mssql_datafiles(string_table: StringTable) -> SectionDatafiles:
    section: dict[_ItemKey, MSSQLInstanceData] = {}
    for line in string_table:
        if line[-1].startswith("ERROR: "):
            continue
        if len(line) == 6:
            inst = None
            database, file_name, physical_name, max_size, allocated_size, used_size = line
            unlimited = False
        elif len(line) == 8:
            inst, database, file_name, physical_name, max_size, allocated_size, used_size = line[:7]
            unlimited = line[7] == "1"
        else:
            continue

        mssql_instance = section.setdefault(
            (inst, database, file_name),
            {
                "unlimited": unlimited,
                "max_size": None,
                "allocated_size": None,
                "used_size": None,
                "mountpoint": physical_name.lower(),
            },
        )
        with suppress(ValueError):
            mssql_instance["max_size"] = float(max_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["allocated_size"] = float(allocated_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["used_size"] = float(used_size) * 1024 * 1024

    return section


agent_section_mssql_datafiles = AgentSection(
    name="mssql_datafiles",
    parse_function=parse_mssql_datafiles,
)

agent_section_mssql_transactionlogs = AgentSection(
    name="mssql_transactionlogs",
    parse_function=parse_mssql_datafiles,
)


@dataclasses.dataclass(frozen=True)
class DatafileUsage:
    used: float
    allocated: float
    max: float


def _format_item_mssql_datafiles(
    inst: str | None,
    database: str,
    file_name: str | None,
) -> str:
    if inst is None:
        return f"{database}.{file_name}"
    if file_name is None:
        return f"{inst}.{database}"
    return f"{inst}.{database}.{file_name}"


def _mssql_datafiles_process_sizes(
    params: Mapping[str, Any],
    datafile_usage: DatafileUsage,
) -> CheckResult:
    def calculate_levels(
        levels: tuple[float, float],
        reference_value: float | None,
    ) -> tuple[float, float] | None:
        if isinstance(levels[0], float):
            if reference_value:
                return (
                    levels[0] * reference_value / 100.0,
                    levels[1] * reference_value / 100.0,
                )
        elif levels[0] is not None:
            return (
                levels[0] * 1024 * 1024,
                levels[1] * 1024 * 1024,
            )

        return None

    for param_key, name, perf_key, value, reference_value in [
        (
            "used_levels",
            "Used",
            "data_size",
            datafile_usage.used,
            datafile_usage.max,
        ),
        (
            "allocated_used_levels",
            "Allocated used",
            None,
            datafile_usage.used,
            datafile_usage.allocated,
        ),
        (
            "allocated_levels",
            "Allocated",
            "allocated_size",
            datafile_usage.allocated,
            datafile_usage.max,
        ),
    ]:
        raw_levels = params.get(param_key, (None, None))
        if isinstance(raw_levels, list):
            levels = None
            for level_set in raw_levels:
                if datafile_usage.max > level_set[0]:
                    levels = calculate_levels(level_set[1], reference_value)
                    break
        else:
            levels = calculate_levels(raw_levels, reference_value)

        yield from check_levels_v1(
            value,
            metric_name=perf_key,
            levels_upper=levels,
            render_func=render.bytes,
            label=name,
            boundaries=(0, reference_value),
        )

    yield Result(
        state=State.OK,
        summary=f"Maximum size: {render.bytes(datafile_usage.max)}",
    )


def _get_mountpoint(
    df_dict: Mapping[str, object],
    physical_name: str,
) -> str:
    part = physical_name.split("\\")
    i = len(part)
    while i > 1:
        i = i - 1
        mountpoint = df_dict.get("/".join(part[0:i]) + "/")
        if mountpoint is not None:
            return "/".join(part[0:i]) + "/"
    return part[0] + "/"


def discover_mssql_common(
    mode: Literal["datafiles", "transactionlogs"],
    params: list[Mapping[str, Any]],
    section: SectionDatafiles,
) -> DiscoveryResult:
    summarize = params[0].get("summarize_%s" % mode, False)
    for inst, database, file_name in section:
        yield Service(
            item=_format_item_mssql_datafiles(
                inst,
                database,
                None if summarize else file_name,
            ),
        )


def discover_mssql_datafiles(
    params: list[Mapping[str, Any]],
    section_mssql_datafiles: SectionDatafiles | None,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> DiscoveryResult:
    if not section_mssql_datafiles:
        return
    yield from discover_mssql_common("datafiles", params, section_mssql_datafiles)


def discover_mssql_transactionlogs(
    params: list[Mapping[str, Any]],
    section_mssql_transactionlogs: SectionDatafiles | None,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> DiscoveryResult:
    if not section_mssql_transactionlogs:
        return
    yield from discover_mssql_common("transactionlogs", params, section_mssql_transactionlogs)


def _datafile_usage(
    instances: Sequence[MSSQLInstanceData],
    available_bytes: Mapping[str, float],
) -> DatafileUsage:
    max_size_sum = 0.0
    allocated_size_sum = 0.0
    used_size_sum = 0.0
    unlimited = False
    used_mointpoints = []

    for instance in instances:
        unlimited |= instance["unlimited"]
        allocated_size_sum += instance["allocated_size"] or 0
        used_size_sum += (used_size := instance["used_size"] or 0)
        mountpoint = _get_mountpoint(available_bytes, instance["mountpoint"])
        filesystem_free_size = available_bytes.get(mountpoint)
        if mountpoint in used_mointpoints:
            filesystem_free_size = 0
        else:
            used_mointpoints.append(mountpoint)
        max_size = _effective_max_size(
            instance["max_size"],
            filesystem_free_size,
            used_size,
            unlimited,
        )
        max_size_sum += max_size

    return DatafileUsage(
        used=used_size_sum,
        allocated=allocated_size_sum,
        max=max_size_sum,
    )


def _effective_max_size(
    max_size: float | None,
    free_size: float | None,
    used_size: float,
    unlimited: bool,
) -> float:
    max_size_float = max_size or 0

    if free_size is None:
        return max_size_float

    total_size = free_size + used_size

    if unlimited:
        return total_size

    return min(max_size_float, total_size)


def check_mssql_common(
    item: str,
    params: Mapping[str, Any],
    section: SectionDatafiles,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> CheckResult:
    if not (
        instances_for_item := [
            values
            for (inst, database, file_name), values in section.items()
            if (
                _format_item_mssql_datafiles(inst, database, file_name) == item
                or _format_item_mssql_datafiles(inst, database, None) == item
            )
        ]
    ):
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Failed to connect to database")

    yield from _mssql_datafiles_process_sizes(
        params,
        _datafile_usage(
            instances_for_item,
            available_bytes=(
                {f.mountpoint.lower(): f.avail_mb * 1024 * 1024 for f in section_df[0]}
                if section_df
                else {}
            ),
        ),
    )


def check_mssql_datafiles(
    item: str,
    params: Mapping[str, Any],
    section_mssql_datafiles: SectionDatafiles | None,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> CheckResult:
    if not section_mssql_datafiles:
        return

    yield from check_mssql_common(
        item,
        params,
        section_mssql_datafiles,
        section_df,
    )


def check_mssql_transactionlogs(
    item: str,
    params: Mapping[str, Any],
    section_mssql_transactionlogs: SectionDatafiles | None,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,
) -> CheckResult:
    if not section_mssql_transactionlogs:
        return

    yield from check_mssql_common(
        item,
        params,
        section_mssql_transactionlogs,
        section_df,
    )


check_plugin_mssql_datafiles = CheckPlugin(
    name="mssql_datafiles",
    sections=["mssql_datafiles", "df"],
    service_name="MSSQL Datafile %s",
    discovery_function=discover_mssql_datafiles,
    discovery_ruleset_name="mssql_transactionlogs_discovery",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={
        "summarize_datafiles": False,
        "summarize_transactionlogs": False,
    },
    check_function=check_mssql_datafiles,
    check_default_parameters={"used_levels": (80.0, 90.0)},
    check_ruleset_name="mssql_datafiles",
)

check_plugin_mssql_transactionlogs = CheckPlugin(
    name="mssql_transactionlogs",
    sections=["mssql_transactionlogs", "df"],
    service_name="MSSQL Transactionlog %s",
    discovery_function=discover_mssql_transactionlogs,
    discovery_ruleset_name="mssql_transactionlogs_discovery",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={
        "summarize_datafiles": False,
        "summarize_transactionlogs": False,
    },
    check_function=check_mssql_transactionlogs,
    check_default_parameters={"used_levels": (80.0, 90.0)},
    check_ruleset_name="mssql_transactionlogs",
)
