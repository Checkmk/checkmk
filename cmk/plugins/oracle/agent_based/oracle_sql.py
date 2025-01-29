#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cache_helper import CacheInfo, render_cache_info

# <<<oracle_sql:sep(58)>>>
# [[[SID-1|SQL-A|cached(123,456)]]]
# details:DETAILS
# perfdata:NAME=VAL;WARN;CRIT;MIN;MAX NAME=VAL;WARN;CRIT;MIN;MAX ...
# perfdata:NAME=VAL;WARN;CRIT;MIN;MAX ...
# long:LONG
# long:LONG
# ...
# exit:CODE
# elapsed:TS
# [[[SID-2|SQL-B]]]
# details:DETAILS
# perfdata:
# long:LONG
# long:LONG
# ...
# exit:CODE
# elapsed:TS


@dataclass
class Instance:
    details: list[str] = field(default_factory=lambda: [])
    metrics: list[Metric] = field(default_factory=lambda: [])
    long: list[str] = field(default_factory=lambda: [])
    exit: int = 0
    elapsed: float | None = None
    parsing_error: dict[tuple[str, str, int], list[str]] = field(default_factory=lambda: {})
    cache_info: CacheInfo | None = None


def parse_number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


Section = dict[str, Instance]


def parse_metrics(line: str) -> Iterator[Metric]:
    for entry in line.split():
        if not entry:
            continue
        var_name, rest = entry.split("=", 1)
        if ";" not in rest:
            if (value := parse_number(rest)) is not None:
                yield Metric(name=var_name, value=value)
            continue

        value, level_min, level_max = map(parse_number, rest.split(";")[0:3])

        if value is None:
            continue

        boundaries = rest.split(";")[3:]

        if len(boundaries) == 2:
            lower, upper = tuple(map(parse_number, boundaries))
            yield Metric(
                name=var_name,
                value=value,
                levels=(level_min, level_max),
                boundaries=(lower, upper),
            )
            continue

        yield Metric(
            name=var_name,
            value=value,
            levels=(level_min, level_max),
        )


def _prepare_instance(line: str, now: float) -> tuple[str, str, Instance]:
    sid, item, *rest = line.split("|")
    instance = Instance()
    if rest:
        instance.cache_info = CacheInfo.from_raw(rest[0], now)
    return sid, item, instance


def parse_oracle_sql(string_table: StringTable) -> Section:
    now = time.time()
    parsed: dict[str, Instance] = {}
    instance = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            sid, item, inst = _prepare_instance(line[0][3:-3], now)
            instance = parsed.setdefault((f"{sid} SQL {item}").upper(), inst)
            continue

        if instance is None:
            continue

        key = line[0]
        infotext = ":".join(line[1:]).strip()
        if key.endswith("ERROR") or key.startswith("ERROR at line") or "|FAILURE|" in key:
            instance.parsing_error.setdefault(("instance", "PL/SQL failure", 2), []).append(
                "{}: {}".format(key.split("|")[-1], infotext)
            )

        elif key in ["details"]:
            instance.details.append(infotext)

        elif key in ["long"]:
            instance.long.append(infotext)

        elif key == "perfdata":
            try:
                instance.metrics += list(parse_metrics(line[1]))
            except Exception:
                instance.parsing_error.setdefault(("metrics", "Metric parse error", 3), []).append(
                    infotext
                )

        elif key == "exit":
            instance.exit = int(line[1])

        elif key == "elapsed":
            if line[1] != "":
                instance.elapsed = float(line[1])

        else:
            instance.parsing_error.setdefault(
                ("unknown", f'Unexpected Keyword: "{key}". Line was', 3), []
            ).append(":".join(line).strip())

    return parsed


def discovery_oracle_sql(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_oracle_sql(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return

    data = section[item]
    for (error_key, error_title, error_state), error_lines in data.parsing_error.items():
        yield Result(
            state=State(params.get("%s_error_state" % error_key, error_state)),
            summary="{}: {}".format(error_title, " ".join(error_lines)),
        )

    metrics = data.metrics
    elapsed_time = data.elapsed
    if elapsed_time is not None:
        metrics.append(Metric(name="elapsed_time", value=elapsed_time))

    if details := data.details:
        yield Result(state=State(data.exit), summary=", ".join(details))
        yield from metrics

    if long := data.long:
        long_details = "%s" % "\n".join(long[1:])
        yield Result(
            state=State.OK, summary=long[0], details=long_details if long_details else None
        )

    if data.cache_info is not None:
        yield Result(state=State.OK, summary=render_cache_info(data.cache_info))


agent_section_oracle_sql = AgentSection(
    name="oracle_sql",
    parse_function=parse_oracle_sql,
)


check_plugin_oracle_sql = CheckPlugin(
    name="oracle_sql",
    discovery_function=discovery_oracle_sql,
    check_function=check_oracle_sql,
    service_name="ORA %s",
    check_ruleset_name="oracle_sql",
    check_default_parameters={},
)
