#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Literal, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
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

# <<<inotify:sep(9)>>>
# configured folder    /tmp/noti
# configured file  /tmp/noti/test
# configured file  /tmp/noti/other
# 1465470055  modify  /tmp/noti/test  5   1465470055
# 1465470055  open    /tmp/noti/test  5   1465470055
# 1465470055  modify  /tmp/noti/test  5   1465470055
# 1465470056  modify  /tmp/noti/test  5   1465470056
# 1465470056  open    /tmp/noti/test  5   1465470056

_Mode2Time = Mapping[str, int]


class Section(NamedTuple):
    warnings: Counter[str]
    configured: Mapping[str, Literal["file", "folder"]]
    stats: Mapping[str, _Mode2Time]


def parse_inotify(string_table: StringTable) -> Section:
    warnings: Counter[str] = Counter()
    configured: dict[str, Literal["file", "folder"]] = {}
    stats: dict[str, dict[str, int]] = defaultdict(dict)

    for line in string_table:
        if line[0].startswith("warning"):
            warnings[line[1]] += 1
            continue
        if line[0].startswith("configured"):
            configured[line[2]] = "file" if line[1] == "file" else "folder"
            continue

        time_stamp, mode, filepath, *_unused = line

        stats[filepath][mode] = int(time_stamp)
        stats[os.path.dirname(filepath)][mode] = int(time_stamp)

    return Section(warnings, configured, stats)


def discover_inotify(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=f"{type_.title()} {path}") for path, type_ in section.configured.items()
    )


def check_inotify(
    item: str, params: Mapping[str, list[tuple[str, float, float]]], section: Section
) -> CheckResult:
    value_store = get_value_store()
    last_status = value_store.get("last_operations", {})
    now = time.time()
    yield from _check_inotify(item, params, section, last_status, now)
    value_store["last_operations"] = last_status


def _check_inotify(
    item: str,
    params: Mapping[str, list[tuple[str, float, float]]],
    section: Section,
    last_status: dict[str, int],
    now: float,
) -> CheckResult:
    type_, path = item.split(" ", 1)
    if section.configured.get(path) != type_.lower():
        return

    last_status.update(section.stats.get(path, {}))

    levels = {mode: (warn, crit) for mode, warn, crit in params["age_last_operation"]}

    for mode, timestamp in sorted(last_status.items()):
        yield from check_levels_v1(
            now - timestamp,
            levels_upper=levels.get(mode),
            render_func=render.timespan,
            label=f"Time since last {mode}",
        )

    for mode in set(levels) - set(last_status):
        yield Result(state=State.UNKNOWN, summary=f"Time since last {mode}: unknown")

    if section.warnings:
        yield Result(state=State.WARN, summary="Incomplete data!")
        yield from (
            Result(state=State.WARN, summary=f"{count} warning(s): {msg}")
            for msg, count in section.warnings.items()
        )

    if not last_status:
        yield Result(state=State.OK, summary="No data available yet")


agent_section_inotify = AgentSection(
    name="inotify",
    parse_function=parse_inotify,
)

check_plugin_inotify = CheckPlugin(
    name="inotify",
    service_name="INotify %s",
    discovery_function=discover_inotify,
    check_function=check_inotify,
    check_ruleset_name="inotify",
    check_default_parameters={"age_last_operation": []},
)
