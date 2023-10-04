#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.jolokia import parse_jolokia_json_output
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store


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


def transform_units(params):
    """transform 1/min to 1/s and ms/min to %, pre 1.7.0 rules."""
    if "collection_time" in params:
        # new params already!
        return params

    new_params = {}
    if "CollectionTime" in params:
        ms_per_min = params["CollectionTime"]
        new_params["collection_time"] = (ms_per_min[0] / 600.0, ms_per_min[1] / 600.0)
    if "CollectionCount" in params:
        count_rate_per_min = params["CollectionCount"]
        new_params["collection_count"] = (
            count_rate_per_min[0] / 60.0,
            count_rate_per_min[1] / 60.0,
        )
    return new_params


def check_jolokia_jvm_garbagecollectors(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    now = time.time()
    try:
        count = data["CollectionCount"]
        ctime = data["CollectionTime"]
    except KeyError:
        return

    try:
        count_rate = get_rate(get_value_store(), "%s.count" % item, now, count, raise_overflow=True)
    finally:  # initalize 2nd counter!
        ctime_rate = get_rate(get_value_store(), "%s.time" % item, now, ctime, raise_overflow=True)

    params = transform_units(params)

    yield check_levels(
        count_rate,
        "jvm_garbage_collection_count",
        params.get("collection_count"),
        unit="/s",
        infoname="Garbage collections",
    )

    yield check_levels(
        ctime_rate * 10.0,  # ms/s -> %
        "jvm_garbage_collection_time",
        params.get("collection_time"),
        unit="%",
        infoname="Time spent collecting garbage",
    )


check_info["jolokia_jvm_garbagecollectors"] = LegacyCheckDefinition(
    parse_function=parse_jolokia_jvm_garbagecollectors,
    service_name="JVM %s",
    discovery_function=discover_jolokia_jvm_garbagecollectors,
    check_function=check_jolokia_jvm_garbagecollectors,
    check_ruleset_name="jvm_gc",
)
