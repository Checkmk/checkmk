#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

from .liboracle import Error, is_instance_name, Ok, oracle_handle_ora_errors, Parsed

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<<oracle_processes>>>
# TUX2 51 300
# FOOBAR 11 4780

# Columns: SID PROCESSES_COUNT PROCESSES_LIMIT


class OracleProcess(NamedTuple):
    name: str
    processes_count: int
    processes_limit: int


type Section = Mapping[str, Parsed[OracleProcess]]


def parse_oracle_processes(string_table: StringTable) -> Section:
    processes: dict[str, OracleProcess] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if len(line) < 3:
                    continue
                with contextlib.suppress(ValueError):
                    processes[line[0]] = OracleProcess(
                        name=line[0], processes_count=int(line[1]), processes_limit=int(line[2])
                    )

    parsed: dict[str, Parsed[OracleProcess]] = {
        sid: Ok(process) for sid, process in processes.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


agent_section_oracle_processes = AgentSection(
    name="oracle_processes",
    parse_function=parse_oracle_processes,
)


def discover_oracle_processes(section: Section) -> DiscoveryResult:
    yield from (Service(item=sid) for sid in section if is_instance_name(sid))


def check_oracle_processes(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(process):
            yield from _check_process(params, process)


def _check_process(
    params: Mapping[str, tuple[float, float]], process: OracleProcess
) -> CheckResult:
    processes_pct = float(process.processes_count / process.processes_limit) * 100
    warn, crit = params["levels"]

    yield from check_levels_v1(
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


check_plugin_oracle_processes = CheckPlugin(
    name="oracle_processes",
    check_function=check_oracle_processes,
    discovery_function=discover_oracle_processes,
    service_name="ORA %s Processes",
    check_ruleset_name="oracle_processes",
    check_default_parameters={"levels": (70.0, 90.0)},
)
