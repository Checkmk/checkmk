#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<logins>>>
# 3

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}

DiscoveryResult = Iterable[tuple[None, dict]]
CheckResult = Iterable[tuple[int, str, list]]

Section = int


def parse_logins(string_table: StringTable) -> Section | None:
    try:
        return int(string_table[0][0])
    except (IndexError, ValueError):
        return None


def discover_logins(section: Section) -> DiscoveryResult:
    yield None, {}


def check_logins(
    _no_item: None, params: Mapping[str, tuple[int, int]], section: Section
) -> CheckResult:
    yield check_levels(
        section,
        "logins",
        params["levels"],
        infoname="On system",
        human_readable_func=lambda x: "%d" % x,
    )


check_info["logins"] = LegacyCheckDefinition(
    name="logins",
    service_name="Logins",
    parse_function=parse_logins,
    discovery_function=discover_logins,
    check_function=check_logins,
    check_ruleset_name="logins",
    check_default_parameters={
        "levels": (20, 30),
    },
)
