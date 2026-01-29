#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import DiscoveryResult, Service, StringTable
from cmk.base.check_legacy_includes.innovaphone import check_innovaphone

check_info = {}


def discover_innovaphone_channels(string_table: StringTable) -> DiscoveryResult:
    yield from (Service(item=x[0]) for x in string_table if x[1] == "Up" and x[2] == "Up")


def check_innovaphone_channels(
    item: str, params: Mapping[str, Any], info: StringTable
) -> LegacyCheckResult:
    for line in info:
        if line[0] == item:
            link, physical = line[1:3]
            if link != "Up" or physical != "Up":
                yield 2, f"Link: {link}, Physical: {physical}"
                return
            idle, total = map(float, line[3:])
            perc_used = (idle / total) * 100  # fixed: true-division
            perc_free = 100 - perc_used
            message = f"(used: {total - idle:.0f}, free: {idle:.0f}, total: {total:.0f})"
            yield check_innovaphone(params["levels"], [[None, perc_free]], "%", message)
            return


def parse_innovaphone_channels(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_channels"] = LegacyCheckDefinition(
    name="innovaphone_channels",
    parse_function=parse_innovaphone_channels,
    service_name="Channel %s",
    discovery_function=discover_innovaphone_channels,
    check_function=check_innovaphone_channels,
    check_default_parameters={
        "levels": (75.0, 80.0),
    },
)
