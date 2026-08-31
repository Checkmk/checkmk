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
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True, kw_only=True)
class Channel:
    link: str
    physical: str
    idle: float
    total: float

    @property
    def is_up(self) -> bool:
        return self.link == "Up" and self.physical == "Up"


Section = Mapping[str, Channel]


def parse_innovaphone_channels(string_table: StringTable) -> Section:
    return {
        item: Channel(
            link=link,
            physical=physical,
            idle=float(idle),
            total=float(total),
        )
        for item, link, physical, idle, total in string_table
    }


def discover_innovaphone_channels(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, channel in section.items() if channel.is_up)


def check_innovaphone_channels(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (channel := section.get(item)) is None:
        return

    if not channel.is_up:
        yield Result(
            state=State.CRIT, summary=f"Link: {channel.link}, Physical: {channel.physical}"
        )
        return

    perc_used = 100 - (channel.idle / channel.total) * 100
    used = int(perc_used)
    warn, crit = params["levels"]

    yield Result(
        state=State.CRIT if used >= crit else State.WARN if used >= warn else State.OK,
        summary=(
            f"Current: {used}% (used: {channel.total - channel.idle:.0f},"
            f" free: {channel.idle:.0f}, total: {channel.total:.0f})"
        ),
    )
    yield Metric("usage", used, levels=(warn, crit), boundaries=(0, 100))


agent_section_innovaphone_channels = AgentSection(
    name="innovaphone_channels",
    parse_function=parse_innovaphone_channels,
)


check_plugin_innovaphone_channels = CheckPlugin(
    name="innovaphone_channels",
    service_name="Channel %s",
    discovery_function=discover_innovaphone_channels,
    check_function=check_innovaphone_channels,
    check_default_parameters={
        "levels": (75.0, 80.0),
    },
)
