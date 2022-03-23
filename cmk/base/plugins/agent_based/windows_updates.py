#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping, NamedTuple, Optional, Sequence

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class Section(NamedTuple):
    reboot_required: bool
    important_updates: Sequence[str]
    optional_updates: Sequence[str]
    forced_reboot: Optional[float]


def parse_windows_updates(string_table: StringTable) -> Optional[Section]:
    if not string_table or len(string_table[0]) != 3:
        return None

    if string_table[0][0] == "x":
        raise RuntimeError(" ".join(string_table[1]))

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
        forced_reboot: Optional[float] = time.mktime(
            time.strptime(" ".join(next(lines_iter)), "%Y-%m-%d %H:%M:%S")
        )
    except (StopIteration, ValueError):
        forced_reboot = None

    return Section(
        reboot_required=bool(int(string_table[0][0])),
        important_updates=important,
        optional_updates=optional,
        forced_reboot=forced_reboot,
    )


register.agent_section(
    name="windows_updates",
    parse_function=parse_windows_updates,
)


def discover(section: Section) -> DiscoveryResult:
    yield Service()


def check_windows_updates(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels(
        len(section.important_updates),
        metric_name="important",
        levels_upper=params["levels_important"],
        render_func=lambda x: f"{x:d}",
        label="Important",
    )
    if section.important_updates:
        yield Result(state=State.OK, notice=f"({'; '.join(section.important_updates)})")

    yield from check_levels(
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

    yield from check_levels(
        delta,
        levels_lower=params["levels_lower_forced_reboot"],
        render_func=render.timespan,
        label="Time to enforced reboot to finish updates",
    )


register.check_plugin(
    name="windows_updates",
    service_name="System Updates",
    check_ruleset_name="windows_updates",
    discovery_function=discover,
    check_function=check_windows_updates,
    check_default_parameters=dict(
        levels_important=None,
        levels_optional=None,
        levels_lower_forced_reboot=(604800, 172800),
    ),
)
