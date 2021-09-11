#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from typing import Any, Dict, List, Literal, Mapping, Optional, Tuple, TypedDict

from cmk.base.plugins.agent_based.utils.df import BlocksSubsection, InodesSubsection

from .agent_based_api.v1 import check_levels, IgnoreResultsError, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class MSSQLInstanceData(TypedDict):
    unlimited: bool
    max_size: Optional[float]
    allocated_size: Optional[float]
    used_size: Optional[float]
    mountpoint: str


SectionDatafiles = Dict[Tuple[Optional[str], str, str], MSSQLInstanceData]


def parse_mssql_datafiles(string_table: StringTable) -> SectionDatafiles:
    """
    >>> from pprint import pprint
    >>> pprint(parse_mssql_datafiles([
    ...     ['MSSQL46', 'CorreLog_Report_T', 'CorreLog_Report_T_log',
    ...      'Z:\\\\mypath\\\\CorreLog_Report_T_log.ldf', '2097152', '256', '16', '0'],
    ... ]))
    {('MSSQL46', 'CorreLog_Report_T', 'CorreLog_Report_T_log'): {'allocated_size': 268435456.0,
                                                                 'max_size': 2199023255552.0,
                                                                 'mountpoint': 'Z',
                                                                 'unlimited': False,
                                                                 'used_size': 16777216.0}}
    """
    section: SectionDatafiles = {}
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
                "mountpoint": physical_name[0],
            },
        )
        with suppress(ValueError):
            mssql_instance["max_size"] = float(max_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["allocated_size"] = float(allocated_size) * 1024 * 1024
        with suppress(ValueError):
            mssql_instance["used_size"] = float(used_size) * 1024 * 1024

    return section


register.agent_section(
    name="mssql_datafiles",
    parse_function=parse_mssql_datafiles,
)

register.agent_section(
    name="mssql_transactionlogs",
    parse_function=parse_mssql_datafiles,
)


def _format_item_mssql_datafiles(
    inst: Optional[str],
    database: str,
    file_name: Optional[str],
) -> str:
    if inst is None:
        return "%s.%s" % (database, file_name)
    if file_name is None:
        return "%s.%s" % (inst, database)
    return "%s.%s.%s" % (inst, database, file_name)


def _mssql_datafiles_process_sizes(
    params: Mapping[str, Any],
    used_size: float,
    allocated_size: float,
    max_size: Optional[float],
) -> CheckResult:
    def calculate_levels(
        levels: Tuple[float, float],
        reference_value: Optional[float],
    ) -> Optional[Tuple[float, float]]:
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
        ("used_levels", "Used", "data_size", used_size, max_size),
        ("allocated_used_levels", "Allocated used", None, used_size, allocated_size),
        ("allocated_levels", "Allocated", "allocated_size", allocated_size, max_size),
    ]:
        raw_levels = params.get(param_key, (None, None))
        if isinstance(raw_levels, list):
            levels = None
            for level_set in raw_levels:
                if max_size > level_set[0]:
                    levels = calculate_levels(level_set[1], reference_value)
                    break
        else:
            levels = calculate_levels(raw_levels, reference_value)

        yield from check_levels(
            value,
            metric_name=perf_key,
            levels_upper=levels,
            render_func=render.bytes,
            label=name,
            boundaries=(0, reference_value),
        )

    yield Result(
        state=state.OK,
        summary="Maximum size: %s" % ("unlimited" if max_size is None else render.bytes(max_size)),
    )


def discover_mssql_common(
    mode: Literal["datafiles", "transactionlogs"],
    params: List[Mapping[str, Any]],
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
    params: List[Mapping[str, Any]],
    section_mssql_datafiles: Optional[SectionDatafiles],
    section_df: Optional[Tuple[BlocksSubsection, InodesSubsection]],
) -> DiscoveryResult:
    if not section_mssql_datafiles:
        return
    yield from discover_mssql_common("datafiles", params, section_mssql_datafiles)


def discover_mssql_transactionlogs(
    params: List[Mapping[str, Any]],
    section_mssql_transactionlogs: Optional[SectionDatafiles],
    section_df: Optional[Tuple[BlocksSubsection, InodesSubsection]],
) -> DiscoveryResult:
    if not section_mssql_transactionlogs:
        return
    yield from discover_mssql_common("transactionlogs", params, section_mssql_transactionlogs)


def check_mssql_common(
    item: str,
    params: Mapping[str, Any],
    section: SectionDatafiles,
    section_df: Optional[Tuple[BlocksSubsection, InodesSubsection]],
) -> CheckResult:
    max_size_sum = 0.0
    allocated_size_sum = 0.0
    used_size_sum = 0.0
    unlimited = False

    available_bytes = {}
    if section_df:
        available_bytes = {f.mountpoint[0]: f.avail_mb * 1024 * 1024 for f in section_df[0]}

    found = False
    for (inst, database, file_name), values in section.items():
        if (
            _format_item_mssql_datafiles(inst, database, file_name) == item
            or _format_item_mssql_datafiles(inst, database, None) == item
        ):
            found = True
            max_size = values["max_size"]
            filesystem_free_size = available_bytes.get(values["mountpoint"], max_size)
            unlimited = unlimited or values["unlimited"]
            if (max_size or 0) > (filesystem_free_size or 0) or unlimited:
                max_size = filesystem_free_size
            allocated_size = values["allocated_size"]
            used_size = values["used_size"]
            if max_size:
                max_size_sum += max_size
            if allocated_size:
                allocated_size_sum += allocated_size
            if used_size:
                used_size_sum += used_size

    if not found:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Failed to connect to database")

    yield from _mssql_datafiles_process_sizes(
        params, used_size_sum, allocated_size_sum, max_size_sum
    )


def check_mssql_datafiles(
    item: str,
    params: Mapping[str, Any],
    section_mssql_datafiles: Optional[SectionDatafiles],
    section_df: Optional[Tuple[BlocksSubsection, InodesSubsection]],
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
    section_mssql_transactionlogs: Optional[SectionDatafiles],
    section_df: Optional[Tuple[BlocksSubsection, InodesSubsection]],
) -> CheckResult:
    if not section_mssql_transactionlogs:
        return

    yield from check_mssql_common(
        item,
        params,
        section_mssql_transactionlogs,
        section_df,
    )


register.check_plugin(
    name="mssql_datafiles",
    sections=["mssql_datafiles", "df"],
    service_name="MSSQL Datafile %s",
    discovery_function=discover_mssql_datafiles,
    discovery_ruleset_name="mssql_transactionlogs_discovery",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_mssql_datafiles,
    check_default_parameters={"used_levels": (80.0, 90.0)},
    check_ruleset_name="mssql_datafiles",
)

register.check_plugin(
    name="mssql_transactionlogs",
    sections=["mssql_transactionlogs", "df"],
    service_name="MSSQL Transactionlog %s",
    discovery_function=discover_mssql_transactionlogs,
    discovery_ruleset_name="mssql_transactionlogs_discovery",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_mssql_transactionlogs,
    check_default_parameters={"used_levels": (80.0, 90.0)},
    check_ruleset_name="mssql_transactionlogs",
)
