#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.jolokia.agent_based.lib import parse_jolokia_json_output

Section = Mapping[str, Mapping[str, Any]]


def parse_jolokia_jvm_garbagecollectors(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, object]] = {}
    for instance, _mbean, bulk_data in parse_jolokia_json_output(string_table):
        for data in bulk_data.values():
            name = data.get("Name")
            if not name:
                continue
            item = f"{instance} GC {name}"
            parsed.setdefault(item, {}).update(data)

    return parsed


def discover_jolokia_jvm_garbagecollectors(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, data in section.items()
        if -1 not in (data.get("CollectionCount", -1), data.get("CollectionTime", -1))
    )


def check_jolokia_jvm_garbagecollectors(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_jolokia_jvm_garbagecollectors_testable(
        item, params, section, get_value_store(), time.time()
    )


def check_jolokia_jvm_garbagecollectors_testable(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    if not (data := section.get(item)):
        return
    try:
        count = data["CollectionCount"]
        ctime = data["CollectionTime"]
    except KeyError:
        return

    try:
        count_rate = get_rate(value_store, "%s.count" % item, now, count, raise_overflow=True)
    finally:  # initalize 2nd counter!
        ctime_rate = get_rate(value_store, "%s.time" % item, now, ctime, raise_overflow=True)

    yield from check_levels(
        count_rate,
        "jvm_garbage_collection_count",
        params.get("collection_count"),
        human_readable_func=lambda x: f"{x:.2f}/s",
        infoname="Garbage collections",
    )

    yield from check_levels(
        ctime_rate * 0.1,  # ms/s -> %
        "jvm_garbage_collection_time",
        params.get("collection_time"),
        human_readable_func=lambda x: f"{x:.1f}%",
        infoname="Time spent collecting garbage",
    )


agent_section_jolokia_jvm_garbagecollectors = AgentSection(
    name="jolokia_jvm_garbagecollectors",
    parse_function=parse_jolokia_jvm_garbagecollectors,
)


check_plugin_jolokia_jvm_garbagecollectors = CheckPlugin(
    name="jolokia_jvm_garbagecollectors",
    service_name="JVM %s",
    discovery_function=discover_jolokia_jvm_garbagecollectors,
    check_function=check_jolokia_jvm_garbagecollectors,
    check_ruleset_name="jvm_gc",
    check_default_parameters={},
)
