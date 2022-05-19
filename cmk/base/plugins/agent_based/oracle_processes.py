#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, MutableMapping, NamedTuple, Tuple

from .agent_based_api.v1 import (
    check_levels,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    Service,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.oracle import OraErrors

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<<oracle_processes>>>
# TUX2 51 300
# FOOBAR 11 4780

# Columns: SID PROCESSES_COUNT PROCESSES_LIMIT


class OracleProcess(NamedTuple):
    name: str
    processes_count: int
    processes_limit: int


ErrorProcesses = Mapping[str, OraErrors]
OracleProcesses = Mapping[str, OracleProcess]


class SectionOracleProcesses(NamedTuple):
    error_processes: ErrorProcesses
    oracle_processes: OracleProcesses


def parse_oracle_processes(string_table: StringTable) -> SectionOracleProcesses:
    valid_oracle_processes: MutableMapping[str, OracleProcess] = {}
    error_processes: MutableMapping[str, OraErrors] = {}

    for line in string_table:
        ora_error = OraErrors(line)

        if ora_error.ignore:
            continue
        if ora_error.has_error:
            error_processes[line[0]] = ora_error
        else:
            process = line[0]
            valid_oracle_processes[process] = OracleProcess(
                name=process, processes_count=int(line[1]), processes_limit=int(line[2])
            )

    return SectionOracleProcesses(
        error_processes=error_processes, oracle_processes=valid_oracle_processes
    )


register.agent_section(
    name="oracle_processes",
    parse_function=parse_oracle_processes,
)


def discover_oracle_processes(section: SectionOracleProcesses) -> DiscoveryResult:

    for process in section.error_processes:
        yield Service(item=process)

    for process in section.oracle_processes:
        yield Service(item=process)


def check_oracle_processes(
    item: str, params: Mapping[str, Tuple[float, float]], section: SectionOracleProcesses
) -> CheckResult:

    if ora_error := section.error_processes.get(item):
        yield Result(state=ora_error.error_severity, summary=ora_error.error_text)
        return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    if not (process := section.oracle_processes.get(item)):
        raise IgnoreResultsError("Login into database failed")

    processes_pct = float(process.processes_count / process.processes_limit) * 100
    warn, crit = params["levels"]

    yield from check_levels(
        value=processes_pct,
        levels_upper=(warn, crit),
        label=f"{process.processes_count} of {process.processes_limit} processes are used",
        render_func=render.percent,
    )

    yield Metric(
        name="processes",
        value=process.processes_count,
        levels=(process.processes_limit * (warn / 100), process.processes_limit * (crit / 100)),
    )


register.check_plugin(
    name="oracle_processes",
    check_function=check_oracle_processes,
    discovery_function=discover_oracle_processes,
    service_name="ORA %s Processes",
    check_ruleset_name="oracle_processes",
    check_default_parameters={"levels": (70.0, 90.0)},
)
