#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="index"

from cmk.base.check_api import check_levels, discover, LegacyCheckDefinition
from cmk.base.config import check_info


def parse_couchbase_nodes_operations(info):
    parsed = {}
    for line in info:
        if len(line) < 2:
            continue
        raw_value, node = line[0], " ".join(line[1:])
        try:
            parsed[node] = float(raw_value)
        except ValueError:
            continue
    total = sum(parsed.values())
    parsed[None] = total
    return parsed


# We deliberately do not use @get_parsed_item_data here to also account for the case where the
# Couchbase server does 0 operations / sec. This case would result in "UNKN - Item not found in
# agent output" because parsed[item] would evaluate to False in get_parsed_item_data
def check_couchbase_nodes_operations(item, params, parsed):
    if item not in parsed or (not parsed[item] and parsed[item] != 0):
        return None
    return check_levels(parsed[item], "op_s", params.get("ops"), unit="/s")


check_info["couchbase_nodes_operations"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_nodes_operations,
    discovery_function=discover(lambda k, _v: k is not None),
    check_function=check_couchbase_nodes_operations,
    service_name="Couchbase %s Operations",
    check_ruleset_name="couchbase_ops",
)

check_info["couchbase_nodes_operations.total"] = LegacyCheckDefinition(
    discovery_function=discover(lambda k, _v: k is None),
    check_function=check_couchbase_nodes_operations,
    service_name="Couchbase Total Operations",
    check_ruleset_name="couchbase_ops_nodes",
)
