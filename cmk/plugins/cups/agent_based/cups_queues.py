#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output from agent:
# <<<cups_queues>>>
# printer lpr1 disabled since Wed Jun 16 14:21:14 2010 -
#     reason unknown
# printer lpr2 now printing lpr2-3.  enabled since Tue Jun 29 09:22:04 2010
#     Wiederherstellbar: Der Netzwerk-Host „lpr2" ist beschäftigt, erneuter Versuch in 30 Sekunden …
# printer spr1 is idle.  enabled since Thu Mar 11 14:28:23 2010
# printer spr6 disabled since Mon Jun 21 10:29:39 2010 -
#     /usr/lib/cups/backend/lpd failed
# ---
# lpr2-2                  root              1024   Tue Jun 29 09:02:35 2010
# lpr2-3                  root              1024   Tue Jun 29 09:05:54 2010
# zam19-113565 Sebastian Hirschdobler 3561472 Fri Jul 31 12:58:01 2015

# Default thresholds


import time
from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)

_STATE_MAP = {0: State.OK, 1: State.WARN, 2: State.CRIT, 3: State.UNKNOWN}


class _Data(TypedDict):
    status_readable: str
    output: str
    jobs: list[float]


Section = Mapping[str, _Data]


def parse_cups_queues(string_table: list[list[str]]) -> Section:
    parsed: dict[str, _Data] = {}

    for num, line in enumerate(string_table):
        if line[0] == "printer":
            parsed[line[1]] = {
                "status_readable": " ".join(line[2:4]).replace(" ", "_").strip("."),
                "output": " ".join(line[2:]),
                "jobs": [],
            }
            if len(string_table) > num + 1 and string_table[num + 1][0] not in ["printer", "---"]:
                parsed[line[1]]["output"] += " (%s)" % " ".join(string_table[num + 1])
        elif line[0] == "---":
            break

    queue_section = False
    for line in string_table:
        if line[0] == "---":
            queue_section = True
            continue

        item = line[0].split("-", 1)[0]
        if item in parsed and queue_section:
            # Handle different time formats...
            try:  # Tue Jun 29 09:05:54 2010
                job_time = time.mktime(time.strptime(" ".join(line[-5:]), "%a %b %d %H:%M:%S %Y"))
            except Exception:  # Thu 29 Aug 2013 12:41:42 AM CEST
                job_time = time.mktime(
                    time.strptime(" ".join(line[-7:]), "%a %d %b %Y %I:%M:%S %p %Z")
                )
            parsed[item]["jobs"].append(job_time)

    return parsed


def discover_cups_queues(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_cups_queues(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item in section:
        data = section[item]

        if data["status_readable"] in params:
            state = _STATE_MAP.get(params[data["status_readable"]], State.UNKNOWN)
            yield Result(state=state, summary=data["output"])
        else:
            yield Result(state=State.UNKNOWN, summary='Undefinded status output in "lpr -p"')

        now = time.time()
        jobs_count = len(data["jobs"])
        if jobs_count > 0:
            job_count_levels: tuple[int, int] | None = params["job_count"]
            yield from check_levels(
                jobs_count,
                levels_upper=("fixed", job_count_levels) if job_count_levels else None,
                render_func=str,
                label="Jobs",
            )

            oldest = min(data["jobs"])
            yield Result(state=State.OK, summary=f"Oldest job is from {render.datetime(oldest)}")

            job_age_levels: tuple[int, int] | None = params["job_age"]
            yield from check_levels(
                now - oldest,
                levels_upper=("fixed", job_age_levels) if job_age_levels else None,
                render_func=render.timespan,
                label="Age of oldest job",
            )
    else:
        yield Result(state=State.UNKNOWN, summary="Queue not found")


agent_section_cups_queues = AgentSection(
    name="cups_queues",
    parse_function=parse_cups_queues,
)

check_plugin_cups_queues = CheckPlugin(
    name="cups_queues",
    service_name="CUPS Queue %s",
    discovery_function=discover_cups_queues,
    check_function=check_cups_queues,
    check_ruleset_name="cups_queues",
    check_default_parameters={
        "job_count": (5, 10),  # warn/crit for queue entries
        "job_age": (360, 720),  # warn/crit for entry age in seconds
        "is_idle": 0,  # state for "is idle"
        "now_printing": 0,  # state for "now printing"
        "disabled_since": 2,  # state for "disbaled since"
    },
)
