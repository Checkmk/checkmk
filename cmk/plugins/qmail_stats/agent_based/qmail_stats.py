#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class Queue:
    length: int


def parse_qmail_stats(string_table: StringTable) -> Queue:
    return Queue(int(string_table[0][0]))


def discover_qmail_stats(section: Queue) -> DiscoveryResult:
    yield Service()


def check_qmail_stats(params: Mapping[str, Any], section: Queue) -> CheckResult:
    warn, crit = params["deferred"]
    yield from check_levels(
        section.length,
        metric_name="queue",
        levels_upper=("fixed", (warn, crit)),
        render_func=str,
        label="Deferred mails",
    )


agent_section_qmail_stats = AgentSection(
    name="qmail_stats",
    parse_function=parse_qmail_stats,
)

check_plugin_qmail_stats = CheckPlugin(
    name="qmail_stats",
    service_name="Qmail Queue",
    discovery_function=discover_qmail_stats,
    check_function=check_qmail_stats,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters={
        "deferred": (10, 20),
    },
)
