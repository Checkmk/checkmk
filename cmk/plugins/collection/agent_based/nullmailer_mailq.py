#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Collection, Mapping
from typing import NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    StringTable,
)

# Example agent output:
# old format
# <<<nullmailer_mailq>>>
# 8 1

# new format
# <<<nullmailer_mailq>>>
# 8 1 deferred
# 8 1 failed


NULLMAILER_MAILQ_DEFAULT_LEVELS = {
    "deferred": (10, 20),
    "failed": (1, 1),
}


class Queue(NamedTuple):
    size: int
    length: int
    name: str


Section = Collection[Queue]


def parse_nullmailer_mailq(info: StringTable) -> Section:
    def name(line: list[str]) -> str:
        return line[2] if len(line) == 3 else "deferred"

    return [Queue(size=int(line[0]), length=int(line[1]), name=name(line)) for line in info]


def check_single_queue(queue: Queue, upper_levels_length: LevelsT) -> CheckResult:
    make_metric = queue.name == "deferred"

    yield from check_levels(
        value=queue.length,
        metric_name="length" if make_metric else None,
        levels_upper=upper_levels_length,
        render_func=lambda v: "%d mails" % v,
        label=queue.name.capitalize(),
    )

    yield from check_levels(
        value=queue.size,
        metric_name="size" if make_metric else None,
        render_func=render.bytes,
        label="Size",
    )


def check_nullmailer_mailq(params: Mapping[str, tuple[int, int]], section: Section) -> CheckResult:
    for queue in section:
        levels = params.get(queue.name)
        upper_levels_length: LevelsT = ("fixed", levels) if levels else ("no_levels", None)
        yield from check_single_queue(queue, upper_levels_length)


def discover_nullmailer_mailq(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


agent_section_nullmailer_mailq = AgentSection(
    name="nullmailer_mailq",
    parse_function=parse_nullmailer_mailq,
)

check_plugin_nullmailer_mailq = CheckPlugin(
    name="nullmailer_mailq",
    service_name="Nullmailer Queue",
    discovery_function=discover_nullmailer_mailq,
    check_function=check_nullmailer_mailq,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters=NULLMAILER_MAILQ_DEFAULT_LEVELS,
)
