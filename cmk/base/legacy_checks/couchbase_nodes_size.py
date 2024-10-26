#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.couchbase import parse_couchbase_lines

check_info = {}


def discover_couchbase_nodes_size(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_size"] = LegacyCheckDefinition(
    name="couchbase_nodes_size",
    parse_function=parse_couchbase_lines,
    discovery_function=discover_couchbase_nodes_size,
)


def get_couchbase_check_by_keys(key_disk, key_size):
    def check_couchbase_nodes_size(item, params, parsed):
        if not (data := parsed.get(item)):
            return
        on_disk = data.get(key_disk)
        if on_disk is not None:
            yield check_levels(
                on_disk,
                "size_on_disk",
                params.get("size_on_disk"),
                human_readable_func=render.bytes,
                infoname="Size on disk",
            )

        size = data.get(key_size)
        if size is not None:
            yield check_levels(
                size,
                "data_size",
                params.get("size"),
                human_readable_func=render.bytes,
                infoname="Data size",
            )

    return check_couchbase_nodes_size


def discover_couchbase_nodes_size_docs(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_size.docs"] = LegacyCheckDefinition(
    name="couchbase_nodes_size_docs",
    service_name="Couchbase %s Documents",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size_docs,
    check_function=get_couchbase_check_by_keys(
        "couch_docs_actual_disk_size",
        "couch_docs_data_size",
    ),
    check_ruleset_name="couchbase_size_docs",
)


def discover_couchbase_nodes_size_spacial_views(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_size.spacial_views"] = LegacyCheckDefinition(
    name="couchbase_nodes_size_spacial_views",
    service_name="Couchbase %s Spacial Views",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size_spacial_views,
    check_function=get_couchbase_check_by_keys(
        "couch_spatial_disk_size",
        "couch_spatial_data_size",
    ),
    check_ruleset_name="couchbase_size_spacial",
)


def discover_couchbase_nodes_size_couch_views(section):
    yield from ((item, {}) for item in section)


check_info["couchbase_nodes_size.couch_views"] = LegacyCheckDefinition(
    name="couchbase_nodes_size_couch_views",
    service_name="Couchbase %s Couch Views",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size_couch_views,
    check_function=get_couchbase_check_by_keys(
        "couch_views_actual_disk_size",
        "couch_views_data_size",
    ),
    check_ruleset_name="couchbase_size_couch",
)
