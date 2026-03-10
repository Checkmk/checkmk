#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.lib import AZURE_AGENT_SEPARATOR


class Params(TypedDict):
    remaining_reads: LevelsT[int]
    remaining_reads_unknown_state: int


DEFAULT_PARAMS = Params(
    remaining_reads=("no_levels", None),
    remaining_reads_unknown_state=int(State.WARN),
)


@dataclass
class SubscriptionInfo:
    monitored_groups: list[str]
    remaining_reads: int | None


def parse_azure_subscription_info(string_table: StringTable) -> SubscriptionInfo:
    data = {}
    for row in string_table:
        key = row[0]
        value = json.loads(AZURE_AGENT_SEPARATOR.join(row[1:]))
        if key in ("monitored-groups", "remaining-reads"):
            data[key] = value

    return SubscriptionInfo(
        monitored_groups=data["monitored-groups"],
        remaining_reads=data["remaining-reads"],
    )


def discover_azure_subscription_info(section: SubscriptionInfo) -> DiscoveryResult:
    yield Service()


def check_azure_subscription_info(params: Params, section: SubscriptionInfo) -> CheckResult:
    if section.remaining_reads is None:
        yield Result(
            state=State(params["remaining_reads_unknown_state"]),
            summary="Unable to fetch remaining API reads",
        )
    else:
        yield from check_levels(
            section.remaining_reads,
            levels_lower=params["remaining_reads"],
            label="Remaining API reads",
            render_func=lambda f: str(int(f)),
            boundaries=(0, 15000),
        )

    if section.monitored_groups:
        yield Result(
            state=State.OK, summary=f"Monitored groups: {', '.join(section.monitored_groups)}"
        )
    else:
        yield Result(state=State.OK, summary="No monitored groups found")


agent_section_azure_subscription_info = AgentSection(
    name="azure_v2_subscription_info",
    parse_function=parse_azure_subscription_info,
)


check_plugin_azure_subscription_info = CheckPlugin(
    name="azure_v2_subscription_info",
    service_name="Azure subscription info",
    discovery_function=discover_azure_subscription_info,
    check_function=check_azure_subscription_info,
    check_ruleset_name="azure_v2_subscription_info",
    check_default_parameters=DEFAULT_PARAMS,
)
