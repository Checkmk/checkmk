#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

type Section = dict[str | None, Mapping[str, Any]]


def parse_couchbase_buckets_operations(string_table: StringTable) -> Section:
    parsed: Section = dict(parse_couchbase_lines(string_table).items())
    counters = (collections.Counter(data) for data in parsed.values())
    try:
        parsed[None] = sum(counters, collections.Counter())
    except TypeError:
        pass
    return parsed


def discover_couchbase_buckets_operations(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if "ops" in data and item)


def _check_ops_data(data: Mapping[str, Any], params: Mapping[str, Any]) -> CheckResult:
    ops = data.get("ops")
    if ops is not None:
        yield from check_levels(
            ops,
            "op_s",
            params.get("ops"),
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Total (per server)",
        )

    cmd_get = data.get("cmd_get")
    if cmd_get is not None:
        yield from check_levels(
            cmd_get,
            None,
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Gets",
        )

    cmd_set = data.get("cmd_set")
    if cmd_set is not None:
        yield from check_levels(
            cmd_set,
            None,
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Sets",
        )

    creates = data.get("ep_ops_create")
    if creates is not None:
        yield from check_levels(
            creates,
            None,
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Creates",
        )

    updates = data.get("ep_ops_update")
    if updates is not None:
        yield from check_levels(
            updates,
            None,
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Updates",
        )

    deletes = data.get("ep_num_ops_del_meta")
    if deletes is not None:
        yield from check_levels(
            deletes,
            None,
            None,
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Deletes",
        )


def check_couchbase_buckets_operations(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from _check_ops_data(data, params)


def discover_couchbase_buckets_operations_total(section: Section) -> DiscoveryResult:
    if None in section and "ops" in section[None]:
        yield Service()


def check_couchbase_buckets_operations_total(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(None)):
        return
    yield from _check_ops_data(data, params)


agent_section_couchbase_buckets_operations = AgentSection(
    name="couchbase_buckets_operations",
    parse_function=parse_couchbase_buckets_operations,
)


check_plugin_couchbase_buckets_operations = CheckPlugin(
    name="couchbase_buckets_operations",
    service_name="Couchbase Bucket %s Operations",
    discovery_function=discover_couchbase_buckets_operations,
    check_function=check_couchbase_buckets_operations,
    check_ruleset_name="couchbase_ops",
    check_default_parameters={},
)


check_plugin_couchbase_buckets_operations_total = CheckPlugin(
    name="couchbase_buckets_operations_total",
    service_name="Couchbase Bucket Operations",
    sections=["couchbase_buckets_operations"],
    discovery_function=discover_couchbase_buckets_operations_total,
    check_function=check_couchbase_buckets_operations_total,
    check_ruleset_name="couchbase_ops_buckets",
    check_default_parameters={},
)
