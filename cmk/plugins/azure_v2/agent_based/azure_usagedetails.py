#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.lib import parse_resources

Section = Mapping[str, Any]


def parse_azure_usagedetails(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}
    for detail in parse_resources(string_table).values():
        props = detail.properties
        service_name = props["ResourceType"].split("/")[0]
        data = parsed.setdefault(
            service_name,
            {
                "costs": collections.Counter(),
                "subscription_id": detail.subscription,
            },
        )
        data["costs"].update({props["Currency"]: props["Cost"]})

    if parsed:
        parsed["Summary"] = {
            "costs": sum((d["costs"] for d in list(parsed.values())), collections.Counter()),
            # use any subscription_id, they're all the same
            "subscription_id": list(parsed.values())[0]["subscription_id"],
        }

    return parsed


def discover_azure_usagedetails(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_azure_usagedetails(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        raise IgnoreResultsError("Data not present at the moment")

    for currency, amount in list(data.get("costs", {}).items()):
        levels = params.get("costs")
        yield from check_levels(
            value=amount,
            levels_upper=levels,
            metric_name="service_costs_%s" % currency.lower(),
            render_func=lambda v: f"{v:.2f} {currency}",
        )

    yield Result(state=State.OK, summary=f"Subscription: {data['subscription_id']}")


agent_section_azure_virtualmachines = AgentSection(
    name="azure_v2_usagedetails",
    parse_function=parse_azure_usagedetails,
)

check_plugin_azure_usagedetails = CheckPlugin(
    name="azure_v2_usagedetails",
    sections=["azure_v2_usagedetails"],
    service_name="Azure/Costs %s",
    discovery_function=discover_azure_usagedetails,
    check_function=check_azure_usagedetails,
    check_ruleset_name="azure_v2_usagedetails",
    check_default_parameters={},
)
