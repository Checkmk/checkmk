#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="index"

import collections

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib.couchbase import parse_couchbase_lines

check_info = {}


def parse_couchbase_buckets_operations(string_table):
    parsed = parse_couchbase_lines(string_table)
    counters = (collections.Counter(data) for data in parsed.values())
    try:
        parsed[None] = sum(counters, collections.Counter())
    except TypeError:
        pass
    return parsed


def discover_couchbase_buckets_operations(section):
    yield from ((item, {}) for item, data in section.items() if "ops" in data)


def check_couchbase_buckets_operations(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    ops = data.get("ops")
    if ops is not None:
        yield check_levels(
            ops,
            "op_s",
            params.get("ops"),
            unit="/s",
            infoname="Total (per server)",
        )

    cmd_get = data.get("cmd_get")
    if cmd_get is not None:
        yield check_levels(
            cmd_get,
            None,
            None,
            unit="/s",
            infoname="Gets",
        )

    cmd_set = data.get("cmd_set")
    if cmd_set is not None:
        yield check_levels(
            cmd_set,
            None,
            None,
            unit="/s",
            infoname="Sets",
        )

    creates = data.get("ep_ops_create")
    if creates is not None:
        yield check_levels(
            creates,
            None,
            None,
            unit="/s",
            infoname="Creates",
        )

    updates = data.get("ep_ops_update")
    if updates is not None:
        yield check_levels(
            updates,
            None,
            None,
            unit="/s",
            infoname="Updates",
        )

    deletes = data.get("ep_num_ops_del_meta")
    if deletes is not None:
        yield check_levels(
            deletes,
            None,
            None,
            unit="/s",
            infoname="Deletes",
        )


check_info["couchbase_buckets_operations"] = LegacyCheckDefinition(
    name="couchbase_buckets_operations",
    parse_function=parse_couchbase_buckets_operations,
    service_name="Couchbase Bucket %s Operations",
    discovery_function=discover_couchbase_buckets_operations,
    check_function=check_couchbase_buckets_operations,
    check_ruleset_name="couchbase_ops",
)

check_info["couchbase_buckets_operations.total"] = LegacyCheckDefinition(
    name="couchbase_buckets_operations_total",
    service_name="Couchbase Bucket Operations",
    sections=["couchbase_buckets_operations"],
    discovery_function=discover_couchbase_buckets_operations,
    check_function=check_couchbase_buckets_operations,
    check_ruleset_name="couchbase_ops_buckets",
)
