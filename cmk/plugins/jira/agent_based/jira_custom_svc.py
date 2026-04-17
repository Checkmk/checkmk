#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jira_custom_svc>>>
# {"Jira custom 2": {"count": 3200}, "Custom avg": {"avg_sum": 42.0,
# "avg_total": 50, "avg": "0.84"}} {"Custom Service Count": {"count": 270},
# "Custom Service Sum": {"sum": 17.0}, "Custom Service AVG": {"avg": "0.34"}}

import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def parse_jira_custom_svc(string_table: StringTable) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}

    for line in string_table:
        custom_svc = json.loads(" ".join(line))

        for service in custom_svc:
            svc_values = custom_svc.get(service)
            if svc_values is None:
                continue

            try:
                parsed.setdefault(service.title(), {}).update(svc_values)
            except KeyError:
                pass

    return parsed


def check_jira_custom_svc(
    item: str, params: Mapping[str, Any], section: dict[str, dict[str, Any]]
) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    msg_error = item_data.get("error")
    if msg_error is not None:
        yield Result(
            state=State.CRIT,
            summary="Jira error while searching (see long output for details)",
            details=f"Jira error while searching (see long output for details)\n{msg_error}",
        )
        return

    for computation, infotext, hr_func in [
        ("count", "Total number of issues", int),
        ("sum", "Result of summed up values", int),
        ("avg", "Average value", float),
    ]:
        svc_value = item_data.get(computation)
        if svc_value is None:
            continue

        if computation == "avg":
            svc_value = float(svc_value)

        upper_level = params.get(f"custom_svc_{computation}_upper", (None, None))
        lower_level = params.get(f"custom_svc_{computation}_lower", (None, None))

        yield from check_levels(
            svc_value,
            f"jira_{computation}",
            upper_level + lower_level,
            human_readable_func=hr_func,
            infoname=infotext,
        )

        if computation == "avg":
            avg_total = item_data.get("avg_total")
            avg_sum = item_data.get("avg_sum")
            if avg_total is not None and avg_sum is not None:
                yield Result(
                    state=State.OK,
                    summary=f"(Summed up values: {avg_sum} / Total search results: {avg_total})",
                )

        else:
            diff_key = f"{computation}_diff"
            timespan = params.get(diff_key, 604800)
            diff_levels_upper = params.get(f"{diff_key}_upper", (None, None))
            diff_levels_lower = params.get(f"{diff_key}_lower", (None, None))

            diff = _get_value_diff(f"jira_{diff_key}", svc_value, timespan)

            yield from check_levels(
                diff,
                "jira_diff",
                diff_levels_upper + diff_levels_lower,
                infoname=f"Difference last {render.time_offset(timespan)}",
            )


def _get_value_diff(diff_name: str, svc_value: int | float, timespan: int) -> int | float:
    this_time = time.time()
    value_store = get_value_store()

    old_state = value_store.get(diff_name)

    # first call: take current value as diff or assume 0.0
    if old_state is None:
        diff_val = 0
        value_store[diff_name] = (this_time, svc_value)
        return diff_val

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = max(this_time - last_time, 0)
    if timedif < float(timespan):
        diff_val = svc_value - last_val
    else:
        diff_val = 0
        value_store[diff_name] = (this_time, svc_value)

    return diff_val


def discover_jira_custom_svc(section: dict[str, dict[str, Any]]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_jira_custom_svc = AgentSection(
    name="jira_custom_svc",
    parse_function=parse_jira_custom_svc,
)


check_plugin_jira_custom_svc = CheckPlugin(
    name="jira_custom_svc",
    service_name="Jira %s",
    discovery_function=discover_jira_custom_svc,
    check_function=check_jira_custom_svc,
    check_ruleset_name="jira_custom_svc",
    check_default_parameters={},
)
