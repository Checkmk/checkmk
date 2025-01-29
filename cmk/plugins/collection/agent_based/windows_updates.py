#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


# todo(sk): Replace this ugly named tuple with dataclass
class Section(NamedTuple):
    reboot_required: bool
    important_updates: Sequence[str]
    optional_updates: Sequence[str]
    forced_reboot: float | None
    failed: str | None


def _failed_section(reason: str) -> Section:
    return Section(
        reboot_required=False,
        important_updates=[],
        optional_updates=[],
        forced_reboot=None,
        failed=reason,
    )


def parse_windows_updates(string_table: StringTable) -> Section | None:
    if not string_table or len(string_table[0]) != 3:
        return None

    if string_table[0][0] == "x":
        return _failed_section(" ".join(string_table[1]))

    important_updates_count = int(string_table[0][1])
    optional_updates_count = int(string_table[0][2])

    lines_iter = iter(string_table[1:])

    important = (
        [u.strip() for u in " ".join(next(lines_iter)).split(";")]
        if important_updates_count
        else []
    )
    optional = (
        [u.strip() for u in " ".join(next(lines_iter)).split(";")] if optional_updates_count else []
    )

    try:
        forced_reboot: float | None = time.mktime(
            time.strptime(" ".join(next(lines_iter)), "%Y-%m-%d %H:%M:%S")
        )
    except (StopIteration, ValueError):
        forced_reboot = None

    return Section(
        reboot_required=bool(int(string_table[0][0])),
        important_updates=important,
        optional_updates=optional,
        forced_reboot=forced_reboot,
        failed=None,
    )


agent_section_windows_updates = AgentSection(
    name="windows_updates",
    parse_function=parse_windows_updates,
)


# NOTE: section can't be renamed to _section due to creative logic
def discover(section: Section) -> DiscoveryResult:
    yield Service()


def check_windows_updates(params: Mapping[str, Any], section: Section) -> CheckResult:
    if section.failed:
        yield Result(state=State.CRIT, notice=f"({section.failed})")

    yield from check_levels_v1(
        len(section.important_updates),
        metric_name="important",
        levels_upper=params["levels_important"],
        render_func=lambda x: f"{x:d}",
        label="Important",
    )
    if section.important_updates:
        yield Result(state=State.OK, notice=f"({'; '.join(section.important_updates)})")

    yield from check_levels_v1(
        len(section.optional_updates),
        metric_name="optional",
        levels_upper=params["levels_optional"],
        render_func=lambda x: f"{x:d}",
        label="Optional",
    )

    if section.reboot_required:
        yield Result(state=State.WARN, summary="Reboot required to finish updates")

    if not section.forced_reboot or (delta := section.forced_reboot - time.time()) < 0:
        return

    yield from check_levels_v1(
        delta,
        levels_lower=params["levels_lower_forced_reboot"],
        render_func=render.timespan,
        label="Time to enforced reboot to finish updates",
    )


check_plugin_windows_updates = CheckPlugin(
    name="windows_updates",
    service_name="System Updates",
    check_ruleset_name="windows_updates",
    discovery_function=discover,
    check_function=check_windows_updates,
    check_default_parameters={
        "levels_important": (1, 1),
        "levels_optional": (1, 99),
        "levels_lower_forced_reboot": (604800, 172800),
    },
)
