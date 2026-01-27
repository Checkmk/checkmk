#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store
from cmk.plugins.jolokia.agent_based.lib import parse_jolokia_json_output

check_info = {}


def parse_jolokia_jvm_garbagecollectors(string_table):
    parsed = {}
    for instance, _mbean, bulk_data in parse_jolokia_json_output(string_table):
        for data in bulk_data.values():
            name = data.get("Name")
            if not name:
                continue
            item = f"{instance} GC {name}"
            parsed.setdefault(item, {}).update(data)

    return parsed


def discover_jolokia_jvm_garbagecollectors(section):
    yield from (
        (item, {})
        for item, data in section.items()
        if -1 not in (data.get("CollectionCount", -1), data.get("CollectionTime", -1))
    )


def check_jolokia_jvm_garbagecollectors(item, params, parsed):
    yield from check_jolokia_jvm_garbagecollectors_testable(
        item, params, parsed, get_value_store(), time.time()
    )


def check_jolokia_jvm_garbagecollectors_testable(item, params, parsed, value_store, now):
    if not (data := parsed.get(item)):
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

    yield check_levels(
        count_rate,
        "jvm_garbage_collection_count",
        params.get("collection_count"),
        human_readable_func=lambda x: f"{x:.2f}/s",
        infoname="Garbage collections",
    )

    yield check_levels(
        ctime_rate * 0.1,  # ms/s -> %
        "jvm_garbage_collection_time",
        params.get("collection_time"),
        human_readable_func=lambda x: f"{x:.1f}%",
        infoname="Time spent collecting garbage",
    )


check_info["jolokia_jvm_garbagecollectors"] = LegacyCheckDefinition(
    name="jolokia_jvm_garbagecollectors",
    parse_function=parse_jolokia_jvm_garbagecollectors,
    service_name="JVM %s",
    discovery_function=discover_jolokia_jvm_garbagecollectors,
    check_function=check_jolokia_jvm_garbagecollectors,
    check_ruleset_name="jvm_gc",
)
