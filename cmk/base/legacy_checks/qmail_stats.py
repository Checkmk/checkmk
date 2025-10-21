#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import StringTable

check_info = {}


@dataclass(frozen=True)
class Queue:
    length: int


def parse_qmail_stats(string_table: StringTable) -> Queue:
    return Queue(int(string_table[0][0]))


def discover_qmail_stats(section: Queue) -> LegacyDiscoveryResult:
    yield None, {}


def check_qmail_stats(
    _no_item: None, params: Mapping[str, Any], section: Queue
) -> LegacyCheckResult:
    yield check_levels(
        section.length,
        "queue",
        params["deferred"],
        infoname="Deferred mails",
        human_readable_func=str,
    )


check_info["qmail_stats"] = LegacyCheckDefinition(
    name="qmail_stats",
    parse_function=parse_qmail_stats,
    service_name="Qmail Queue",
    discovery_function=discover_qmail_stats,
    check_function=check_qmail_stats,
    check_ruleset_name="mail_queue_length_single",
    check_default_parameters={
        "deferred": (10, 20),
    },
)
