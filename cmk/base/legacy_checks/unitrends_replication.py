#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_unitrends_replication(info):
    inventory = []
    for _application, _result, _complete, target, _instance in info:
        if target not in [x[0] for x in inventory]:
            inventory.append((target, None))
    return inventory


def check_unitrends_replication(item, _no_params, info):
    # this never gone be a blessed check :)
    replications = [x for x in info if x[3] == item]
    if len(replications) == 0:
        return 3, "No Entries found"
    not_successfull = [x for x in replications if x[1] != "Success"]
    if len(not_successfull) == 0:
        return 0, "All Replications in the last 24 hours Successfull"
    messages = []
    for _application, result, _complete, target, instance in not_successfull:
        messages.append(f"Target: {target}, Result: {result}, Instance: {instance}  ")
    # TODO: Maybe a good place to use multiline output here
    return 2, "Errors from the last 24 hours: " + "/ ".join(messages)


def parse_unitrends_replication(string_table: StringTable) -> StringTable:
    return string_table


check_info["unitrends_replication"] = LegacyCheckDefinition(
    name="unitrends_replication",
    parse_function=parse_unitrends_replication,
    service_name="Replicaion %s",
    discovery_function=discover_unitrends_replication,
    check_function=check_unitrends_replication,
)
