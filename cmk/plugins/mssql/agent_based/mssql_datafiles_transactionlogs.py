#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import dataclasses
from collections import defaultdict
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
    # sys.database_files:
    # https://learn.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-database-files-transact-sql?view=sql-server-ver17
    # FILEPROPERTY:
    # https://learn.microsoft.com/en-us/sql/t-sql/functions/fileproperty-transact-sql?view=sql-server-ver17
    # before relying on that documentation, make sure it's still the same sql query!
    unlimited: bool
    # sys.database_files.max_size == -1 # -1 = File can grow until the disk is full.
    max_size: float | None
    # sys.database_files.max_size # Maximum file size, in 8-KB pages
    allocated_size: float | None
    # sys.database_files.size # Current size of the file, in 8-KB pages.
    used_size: float | None
    # FILEPROPERTY(sys.database_files.size.name, 'spaceused') # Amount of space that is used by the specified file.
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
        levels: tuple[float, float] | tuple[int, int] | tuple[None, None],
        reference_value: float | None,
    ) -> tuple[float, float] | None:
        match levels:
            case (float(warn), float(crit)):
                if not reference_value:
                    return None
                return (
                    warn * reference_value / 100.0,
                    crit * reference_value / 100.0,
                )
            case (int(warn), int(crit)):
                return (
                    warn * 1024 * 1024,
                    crit * 1024 * 1024,
                )
            case _:
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
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,  # noqa: ARG001
) -> DiscoveryResult:
    if not section_mssql_datafiles:
        return
    yield from discover_mssql_common("datafiles", params, section_mssql_datafiles)


def discover_mssql_transactionlogs(
    params: list[Mapping[str, Any]],
    section_mssql_transactionlogs: SectionDatafiles | None,
    section_df: tuple[BlocksSubsection, InodesSubsection] | None,  # noqa: ARG001
) -> DiscoveryResult:
    if not section_mssql_transactionlogs:
        return
    yield from discover_mssql_common("transactionlogs", params, section_mssql_transactionlogs)


def _datafile_usage(
    instances: Sequence[MSSQLInstanceData],
    free_bytes_per_mountpoint: Mapping[str, float],
) -> DatafileUsage:
    allocated_size_sum = 0.0
    used_size_sum = 0.0

    instances_per_mountpoint: defaultdict[str, list[MSSQLInstanceData]] = defaultdict(list)
    instances_without_mountpoint: list[MSSQLInstanceData] = []
    for instance in instances:
        allocated_size_sum += instance["allocated_size"] or 0
        used_size_sum += instance["used_size"] or 0
        mountpoint = _get_mountpoint(free_bytes_per_mountpoint, instance["mountpoint"])
        if mountpoint in free_bytes_per_mountpoint:
            instances_per_mountpoint[mountpoint].append(instance)
        else:
            instances_without_mountpoint.append(instance)

    max_size_sum = 0.0
    for mountpoint_key, mountpoint_instances in instances_per_mountpoint.items():
        max_size_sum += _aggregate_max_size(
            mountpoint_instances, free_bytes_per_mountpoint[mountpoint_key]
        )

    # no mountpoint information, maybe no df section available?
    # we fall back to each file's configured maximum
    max_size_sum += sum(instance["max_size"] or 0 for instance in instances_without_mountpoint)

    return DatafileUsage(
        used=used_size_sum,
        allocated=allocated_size_sum,
        max=max_size_sum,
    )


def _aggregate_max_size(
    instances: Sequence[MSSQLInstanceData],
    filesystem_free_size: float,
) -> float:
    allocated_sum = 0.0
    headroom_sum = 0.0
    has_unlimited = False
    for instance in instances:
        allocated = instance["allocated_size"] or 0
        allocated_sum += allocated
        if instance["unlimited"]:
            has_unlimited = True
        else:
            headroom_sum += max(0.0, (instance["max_size"] or 0) - allocated)

    usable_free = filesystem_free_size if has_unlimited else min(filesystem_free_size, headroom_sum)
    return allocated_sum + usable_free


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
            free_bytes_per_mountpoint=(
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
