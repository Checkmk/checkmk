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

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


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
            msg = ""
            state = 0
            warn, crit = params["consumerCount"]
            if crit and consumerCount < crit:
                state = 2
                label = "(!!)"
            elif warn and consumerCount < warn:
                state = 1
                label = "(!)"
            if state > 0:
                msg = "%s consuming connections " % consumerCount
                msg += "(Levels Warn/Crit below %s/%s)%s, " % (warn, crit, label)

            label = ""
            warn, crit = params["size"]
            if crit and size >= crit:
                state = 2
                label = "(!!)"
            elif warn and size >= warn:
                state = max(state, 1)
                label = "(!)"
            msg += "Queue Size: %s" % size
            if label != "":
                msg += "(Levels Warn/Crit at %s/%s)%s" % (warn, crit, label)
            msg += ", Enqueue Count: %s, Dequeue Count: %s" % (enqueueCount, dequeueCount)

            perf = [("queue", size, warn, crit), ("enque", enqueueCount), ("deque", dequeueCount)]
            return state, msg, perf
        if line[0].startswith("[[") and line[0][2:-2] == item:
            found = True
    return 2, "Queue not found"


check_info["mq_queues"] = LegacyCheckDefinition(
    service_name="Queue %s",
    discovery_function=inventory_mq_queues,
    check_function=check_mq_queues,
    check_ruleset_name="mq_queues",
    check_default_parameters={
        "size": (None, None),
        "consumerCount": (None, None),
    },
)
