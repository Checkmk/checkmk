#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<sap:sep(9)>>>
# sap_XYZ    1    50 Nagios/Allgemein/Intern/ResponseTime    249 msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/ResponseTimeDialog  249 msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/ResponseTimeDialogRFC   249 msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/ResponseTimeHTTP    9830    msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/FrontendResponseTime    542 msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/LongRunners 120 sec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/ResponseTime(StandardTran.) 7   msec
# sap_XYZ    1    50 Nagios/Allgemein/Intern/UsersLoggedIn   97  -
# sap_XYZ    1    50 SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime    249 msec
# sap_XYZ    1    50 SAP CCMS Monitor Templates/Dialog Overview/Network Time/FrontEndNetTime 80  msec
# sap_XYZ    1    50 SAP CCMS Monitor Templates/Dialog Overview/Standardized Response Time/ResponseTime(StandardTran.)   7   msec
# sap_XYZ    1    50 SAP CCMS Monitor Templates/Dialog Overview/Users Logged On/UsersLoggedIn    97  -

import re
from collections.abc import Mapping, Sequence
from typing import Any, assert_never, Literal, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    RuleSetType,
    Service,
    State,
    StringTable,
)


class Entry(NamedTuple):
    sid: str
    state: State
    path: str
    reading: float | None
    unit: str
    output: str


Section = Sequence[Entry]


# This map converts between the SAP color codes (key values) and the
# nagios state codes
_SAP_NAGIOS_STATE_MAP = {
    0: State.OK,  # GRAY  (inactive or no current info available) -> OK
    1: State.OK,  # GREEN  -> OK
    2: State.WARN,  # YELLOW -> WARNING
    3: State.CRIT,  # RED    -> CRITICAL
}


RESPONSE_TIME_PATH = "SAP CCMS Monitor Templates/Dialog Overview/"


def _safe_float(raw: str) -> float:
    """
    Taken from legacy API for now to allow migration.
    Try to get rid of it!
    """
    try:
        return float(raw)
    except ValueError:
        return 0.0


def parse_sap(string_table: StringTable) -> Section:
    return [
        Entry(
            sid=sid,
            state=_SAP_NAGIOS_STATE_MAP[int(state)],
            path=path,
            reading=None if reading == "-" else _safe_float(reading),
            unit=unit,
            output=" ".join(output),
        )
        for sid, state, _unused, path, reading, unit, *output in string_table
    ]


agent_section_sap = AgentSection(
    name="sap",
    parse_function=parse_sap,
)


def discover_sap_dialog(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=entry.sid)
        for entry in section
        if entry.path == f"{RESPONSE_TIME_PATH}Dialog Response Time/ResponseTime"
    )


def check_sap_dialog(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    # First extract all infos
    dialog = {
        entry.path.split("/")[-1]: (entry.reading, entry.unit)
        for entry in section
        if entry.sid == item
        and entry.path.startswith(RESPONSE_TIME_PATH)
        and entry.reading is not None
    }

    if not dialog:
        # this isn't perfect. Sap data is delivered as piggyback output. Potentially multiple
        # hosts can each send data for multiple sap instances. The data can also overlap.
        # This means technically we may not get here and report then incomplete data if one host is
        # down.
        # And we would get here if the host isn't down if the item has simply disappeared from
        # the output.
        # There is no way inside this check to determine the host(s) that sent the data in info.
        raise IgnoreResultsError("no output about sap dialogs in agent output")

    def perf_clean_key(s: str) -> str:
        return s.replace("(", "_").replace(")", "_").replace(" ", "_").replace(".", "_").rstrip("_")

    # {
    #     'UsersLoggedIn': (2, '-'),
    #     'ResponseTime(StandardTran.)': (6, 'msec'),
    #     'FrontEndNetTime': (0, 'msec'),
    #     'ResponseTime': (77, 'msec'),
    # }
    for key, value in dialog.items():
        yield from check_levels_v1(
            value[0],
            metric_name=perf_clean_key(key),
            levels_upper=params.get(key),
            render_func=lambda x, t=f"%.2f {'' if value[1] == '-' else value[1]}": t % x,
            label=key,
        )


check_plugin_sap_dialog = CheckPlugin(
    name="sap_dialog",
    service_name="%s Dialog",
    sections=["sap"],
    discovery_function=discover_sap_dialog,
    check_function=check_sap_dialog,
    check_default_parameters={},
    check_ruleset_name="sap_dialog",
)

#
# Simple processing of nodes reported by sap agent
#


def discover_sap_value(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    patterns = [(value["match"], value.get("limit_item_levels")) for value in params]

    for entry in section:
        for pattern_choice, limit_item_levels in patterns:
            if sap_value_path_matches(entry.path, pattern_choice):
                discovered_params = {}
                if limit_item_levels:
                    path = "/".join(entry.path.split("/")[-limit_item_levels:])
                    discovered_params["limit_item_levels"] = limit_item_levels
                else:
                    path = entry.path
                yield Service(item=entry.sid + " " + path, parameters=discovered_params)


def sap_value_path_matches(
    path: str, pattern_choice: tuple[Literal["all", "exact", "pattern"], str]
) -> bool:
    choice, pattern = pattern_choice
    match choice:
        case "all":
            return True
        case "pattern":
            return bool(re.match(pattern, path))
        case "exact":
            return path == pattern
        case other:
            assert_never(other)


def check_sap_value(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    status = None
    limit = params.get("limit_item_levels")

    for entry in section:
        this_path = "/".join(entry.path.split("/")[-limit:]) if limit else entry.path

        if entry.sid + " " + this_path == item:
            status = entry.state
            if entry.reading is not None:
                # This is a performance value, has no output
                yield Metric("value", entry.reading)
                output = f"{entry.reading:0.2f}{entry.unit}"
            else:
                # This is a status field without perfdata
                output = entry.output
            break

    if status is None:
        raise IgnoreResultsError("no output about sap value in agent output")

    yield Result(state=status, summary=output)


check_plugin_sap_value = CheckPlugin(
    name="sap_value",
    service_name="%s",
    sections=["sap"],
    discovery_function=discover_sap_value,
    discovery_default_parameters={"match": ("pattern", "$^")},
    discovery_ruleset_name="inventory_sap_values",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_sap_value,
    check_default_parameters={},
)


GroupPatterns = list[tuple[str, str]]
SAPRules = list[tuple[str, tuple[str, str]]]


def _patterns_match(
    name: str, exclusion: str | None, inclusion: str
) -> Literal[False] | re.Match[str] | None:
    if exclusion and re.match(exclusion, name):
        return False
    return re.match(inclusion, name)


def sap_groups_of_value(
    value_name: str,
    patterns: SAPRules,
) -> set[str]:
    return {
        group_name
        for group_name, (inclusion, exclusion) in patterns
        if _patterns_match(value_name, exclusion, inclusion)
    }


def get_patterns_by_group_name(patterns: SAPRules) -> Mapping[str, GroupPatterns]:
    rules_by_group: dict[str, GroupPatterns] = {}
    for group_name, (inclusion, exclusion) in patterns:
        rules_by_group.setdefault(group_name, []).append((inclusion, exclusion))
    return rules_by_group


def discover_sap_value_groups(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    groups: SAPRules = [
        pattern for parameter_set in params for pattern in parameter_set["grouping_patterns"]
    ]
    patterns_by_group = get_patterns_by_group_name(groups)

    yield from (
        Service(item=item, parameters={"_group_relevant_patterns": patterns_by_group[item]})
        for entry in section
        for item in sap_groups_of_value(entry.path, groups)
    )


def check_sap_value_groups(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    try:
        patterns: GroupPatterns = params["_group_relevant_patterns"]
    except KeyError:
        yield Result(
            state=State.UNKNOWN,
            summary="Rules not found. Please rediscover the services of this host",
        )
        return

    # this fake rules instance already only contains relevant patterns
    precompiled_rule = [(item, pattern) for pattern in patterns]

    results = []
    count_ok, count_crit = 0, 0
    for entry in section:
        if item in sap_groups_of_value(entry.path, precompiled_rule):
            output = entry.output if entry.reading is None else ""

            results.append(Result(state=entry.state, notice=entry.path + output))
            if entry.state is not State.OK:
                count_crit += 1
            else:
                count_ok += 1

    if not results:
        raise IgnoreResultsError("no output about sap value groups in agent output")

    yield Result(state=State.OK, summary=f"OK: {count_ok}")
    yield Result(state=State.OK, summary=f"Critical: {count_crit}")
    yield from results


check_plugin_sap_value_groups = CheckPlugin(
    name="sap_value_groups",
    service_name="%s",
    sections=["sap"],
    discovery_function=discover_sap_value_groups,
    discovery_default_parameters={"grouping_patterns": []},
    discovery_ruleset_name="sap_value_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_sap_value_groups,
    check_default_parameters={},
)
