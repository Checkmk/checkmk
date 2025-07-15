#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import collections
from collections.abc import Mapping

from cmk.base.check_legacy_includes.azure import get_data_or_go_stale

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import StringTable
from cmk.plugins.lib.azure import parse_resources

check_info = {}

Section = Mapping[str, Mapping]


def parse_azure_usagedetails(string_table: StringTable) -> Section:
    parsed: dict[str, dict] = {}
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


def check_azure_usagedetails(
    item: str, params: Mapping[str, object], section: Section
) -> LegacyCheckResult:
    data = get_data_or_go_stale(item, section)
    for currency, amount in list(data.get("costs", {}).items()):
        levels = params.get("levels")
        yield check_levels(amount, "service_costs_%s" % currency.lower(), levels, currency)

    yield 0, "Subscription: %s" % data["subscription_id"]


def discover_azure_usagedetails(section: Section) -> LegacyDiscoveryResult:
    yield from ((item, {}) for item in section)


check_info["azure_usagedetails"] = LegacyCheckDefinition(
    name="azure_usagedetails",
    parse_function=parse_azure_usagedetails,
    service_name="Costs %s",
    discovery_function=discover_azure_usagedetails,
    check_function=check_azure_usagedetails,
    check_ruleset_name="azure_usagedetails",
    check_default_parameters={},
)
