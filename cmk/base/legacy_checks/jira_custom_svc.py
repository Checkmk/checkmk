#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<jira_custom_svc>>>
# {"Jira custom 2": {"count": 3200}, "Custom avg": {"avg_sum": 42.0,
# "avg_total": 50, "avg": "0.84"}} {"Custom Service Count": {"count": 270},
# "Custom Service Sum": {"sum": 17.0}, "Custom Service AVG": {"avg": "0.34"}}


# mypy: disable-error-code="var-annotated"

import json
import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_value_store, render

check_info = {}


def parse_jira_custom_svc(string_table):
    parsed = {}

    for line in string_table:
        custom_svc = json.loads(" ".join(line))

        for service in custom_svc:
            svc_values = custom_svc.get(service)
            if svc_values is None:
                continue

            try:
                parsed.setdefault("%s" % service.title(), {}).update(svc_values)
            except KeyError:
                pass

    return parsed


def check_jira_custom_svc(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    if not item_data:
        return

    msg_error = item_data.get("error")
    if msg_error is not None:
        yield 2, "Jira error while searching (see long output for details)\n%s" % msg_error
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

        upper_level = params.get("custom_svc_%s_upper" % computation, (None, None))
        lower_level = params.get("custom_svc_%s_lower" % computation, (None, None))

        yield check_levels(
            svc_value,
            "jira_%s" % computation,
            upper_level + lower_level,
            human_readable_func=hr_func,
            infoname=infotext,
        )

        if computation == "avg":
            avg_total = item_data.get("avg_total")
            avg_sum = item_data.get("avg_sum")
            if avg_total is not None and avg_sum is not None:
                yield 0, f"(Summed up values: {avg_sum} / Total search results: {avg_total})"

        else:
            diff_key = "%s_diff" % computation
            timespan = params.get(diff_key, 604800)
            diff_levels_upper = params.get("%s_upper" % diff_key, (None, None))
            diff_levels_lower = params.get("%s_lower" % diff_key, (None, None))

            diff = _get_value_diff("jira_%s" % diff_key, svc_value, timespan)

            yield check_levels(
                diff,
                "jira_diff",
                diff_levels_upper + diff_levels_lower,
                infoname="Difference last %s" % render.time_offset(timespan),
            )


def _get_value_diff(diff_name, svc_value, timespan):
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


def discover_jira_custom_svc(section):
    yield from ((item, {}) for item in section)


check_info["jira_custom_svc"] = LegacyCheckDefinition(
    name="jira_custom_svc",
    parse_function=parse_jira_custom_svc,
    service_name="Jira %s",
    discovery_function=discover_jira_custom_svc,
    check_function=check_jira_custom_svc,
    check_ruleset_name="jira_custom_svc",
)
