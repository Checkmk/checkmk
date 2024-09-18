#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    RuleSetType,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib import ps
from cmk.plugins.lib.ucd_hr_detection import HR

_HR_PS_STATUS_MAP = {
    "1": ("running", "running", ""),
    "2": ("runnable", "runnable", "waiting for resource"),
    "3": ("not_runnable", "not runnable", "loaded but waiting for event"),
    "4": ("invalid", "invalid", "not loaded"),
}


class HRProcess(NamedTuple):
    name: str
    path: str
    state_key: str
    state_short: str
    state_long: str


Section = Sequence[HRProcess]


def parse_hr_ps(string_table: StringTable) -> Section:
    parsed = []
    for name, path, status in string_table:
        key, short, long_ = _HR_PS_STATUS_MAP.get(status, (status, "unknown[%s]" % status, ""))
        parsed.append(HRProcess(name.strip(":"), path, key, short, long_))
    return parsed


snmp_section_hr_ps = SimpleSNMPSection(
    name="hr_ps",
    parse_function=parse_hr_ps,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.4.2.1",
        oids=[  # HOST-RESOURCES-MIB
            "2",  # hrSWRunName
            "4",  # hrSWRunPath
            "7",  # hrSWRunStatus
        ],
    ),
    detect=HR,
)


def discover_hr_ps(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    discovered_items: dict[str, Mapping[str, Any]] = {}
    for process in section:
        for rule in params[:-1]:  # skip default
            match_name_or_path = rule.get("match_name_or_path")
            match_status = rule.get("match_status")

            matches = _match_hr_process(process, match_name_or_path, match_status, None)
            if not matches:
                continue

            if matches is True:
                match_groups = []
            else:
                match_groups = [g if g else "" for g in matches.groups()]

            service_descr = ps.replace_service_description(
                rule["descr"], match_groups, match_name_or_path
            )

            discovered_items.setdefault(
                service_descr,
                {
                    "match_name_or_path": match_name_or_path,
                    "match_status": match_status,
                    "match_groups": match_groups,
                },
            )
    yield from (Service(item=i, parameters=p) for i, p in discovered_items.items())


def check_hr_ps(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    match_name_or_path = params.get("match_name_or_path")
    match_status = params.get("match_status")
    match_groups = params.get("match_groups")

    count_processes = 0
    processes_by_state: dict[tuple[str, str, str], list[HRProcess]] = {}
    for process in section:
        if _match_hr_process(process, match_name_or_path, match_status, match_groups):
            count_processes += 1
            processes_by_state.setdefault(
                (process.state_key, process.state_short, process.state_long), []
            ).append(process)

    lc, lw, uw, uc = params.get("levels", (None, None, None, None))
    yield from check_levels_v1(
        count_processes,
        metric_name="processes",
        levels_lower=(lw, lc),
        levels_upper=(uw, uc),
        label="Processes",
        render_func=lambda x: str(int(x)),
    )

    process_state_map = dict(params.get("status", []))
    for (state_key, state_short, state_long), processes in processes_by_state.items():
        state = process_state_map.get(state_key, 0)
        if state_long:
            state_info = f"{state_short} ({state_long})"
        else:
            state_info = state_short
        yield Result(state=State(state), summary=f"{len(processes)} {state_info}")


def _match_hr_process(
    process: HRProcess,
    match_name_or_path: Any | None,  # str, tuple, None ???
    match_status: Sequence[str] | None,
    match_groups: list[str] | None,
) -> bool | re.Match[str]:
    if match_status and process.state_key not in match_status:
        return False

    if not match_name_or_path or match_name_or_path == "match_all":
        return True

    match_type, match_pattern = match_name_or_path
    pattern_to_match = {
        "match_name": process.name,
        "match_path": process.path,
    }[match_type]

    if match_pattern is not None and match_pattern.startswith("~"):
        # Regex for complete process name or path
        # skip "~"
        m = re.match(match_pattern[1:], pattern_to_match)
        if not m:
            return False
        if match_groups:
            return m.groups() == tuple(match_groups)
        return m

    # Exact match on name of executable
    return pattern_to_match == match_pattern


check_plugin_hr_ps = CheckPlugin(
    name="hr_ps",
    service_name="Process %s",
    discovery_function=discover_hr_ps,
    discovery_default_parameters={
        "descr": "%s",
        "default_params": {},
    },
    discovery_ruleset_name="discovery_hr_processes_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_hr_ps,
    check_default_parameters={
        "levels": (1, 1, 99999, 99999),
    },
    check_ruleset_name="hr_ps",
)
