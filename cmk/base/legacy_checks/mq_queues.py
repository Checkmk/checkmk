#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# [[SINGLE_ITEM_EXPORT_int_jens]]
# 0 0 0 0
# [[SPRINGAPP-COMMAND-INBOX-DEV]]
# 0 0 15 15
# [[SINGLE_ITEM_EXPORT_INT_jens]]
# 0 0 0 0
# [[DEBITOR_LOCATION]]
# 0 1 84 84
# [[EDATA_SERIALNUMBERQUERY_INBOX]]
# 0 0 0 0


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_mq_queues(info):
    inventory = []
    for line in info:
        if line[0].startswith("[["):
            item = line[0][2:-2]
            inventory.append((item, {}))
    return inventory


def check_mq_queues(item, params, info):
    found = False
    for line in info:
        if found is True:
            size, consumerCount, enqueueCount, dequeueCount = map(int, line)
            consumer_count_upper_levels = params["consumer_count_levels_upper"] or (None, None)
            consumer_count_lower_levels = params["consumer_count_levels_lower"] or (None, None)
            if (
                count_result := check_levels(
                    consumerCount,
                    None,
                    consumer_count_upper_levels + consumer_count_lower_levels,
                    infoname="Consuming connections",
                    human_readable_func=str,
                )
            )[0]:
                yield count_result
            yield check_levels(
                size, "queue", params["size"], infoname="Queue size", human_readable_func=str
            )
            yield check_levels(
                enqueueCount, "enque", None, infoname="Enqueue count", human_readable_func=str
            )
            yield check_levels(
                dequeueCount, "deque", None, infoname="Dequeue count", human_readable_func=str
            )
            return

        if line[0].startswith("[[") and line[0][2:-2] == item:
            found = True


def parse_mq_queues(string_table: StringTable) -> StringTable:
    return string_table


check_info["mq_queues"] = LegacyCheckDefinition(
    name="mq_queues",
    parse_function=parse_mq_queues,
    service_name="Queue %s",
    discovery_function=inventory_mq_queues,
    check_function=check_mq_queues,
    check_ruleset_name="mq_queues",
    check_default_parameters={
        "size": None,
        "consumer_count_levels_upper": None,
        "consumer_count_levels_lower": None,
    },
)
