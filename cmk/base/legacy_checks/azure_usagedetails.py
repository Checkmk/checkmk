#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import collections

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.azure import get_data_or_go_stale, parse_resources
from cmk.base.config import check_info


def parse_azure_usagedetails(string_table):
    parsed = {}
    for detail in list(parse_resources(string_table).values()):
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


@get_data_or_go_stale
def check_azure_usagedetails(_no_item, params, data):
    for currency, amount in list(data.get("costs", {}).items()):
        levels = params.get("levels")
        yield check_levels(amount, "service_costs_%s" % currency.lower(), levels, currency)

    yield 0, "Subscription: %s" % data["subscription_id"]


def discover_azure_usagedetails(section):
    yield from ((item, {}) for item in section)


check_info["azure_usagedetails"] = LegacyCheckDefinition(
    parse_function=parse_azure_usagedetails,
    service_name="Costs %s",
    discovery_function=discover_azure_usagedetails,
    check_function=check_azure_usagedetails,
    check_ruleset_name="azure_usagedetails",
    check_default_parameters={},
)
