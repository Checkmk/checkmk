#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# <<<elasticsearch_nodes>>>
# mynode1 open_file_descriptors 434
# mynode1 max_file_descriptors 4096
# mynode1 cpu_percent 0
# mynode1 cpu_total_in_millis 167010
# mynode1 mem_total_virtual_in_bytes 7126290432
# mynode2 open_file_descriptors 430
# mynode2 max_file_descriptors 4096
# mynode2 cpu_percent 0
# mynode2 cpu_total_in_millis 151810
# mynode2 mem_total_virtual_in_bytes 7107313664


# mypy: disable-error-code="var-annotated,arg-type"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}

nodes_info = {
    "open_file_descriptors": "Open file descriptors",
    "max_file_descriptors": "Max file descriptors",
    "cpu_percent": "CPU used",
    "cpu_total_in_millis": "CPU total in ms",
    "mem_total_virtual_in_bytes": "Total virtual memory",
}


def parse_elasticsearch_nodes(string_table):
    parsed = {}

    for name, desc, value_str in string_table:
        try:
            if desc == "cpu_percent":
                value = float(value_str)
            else:
                value = int(value_str)

            parsed.setdefault(name, {}).setdefault(desc, (value, nodes_info[desc]))

        except (IndexError, ValueError):
            pass

    return parsed


def check_elasticsearch_nodes(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    for data_key, params_key, hr_func in [
        ("cpu_percent", "cpu_levels", render.percent),
        ("cpu_total_in_millis", "cpu_total_in_millis", int),
        ("mem_total_virtual_in_bytes", "mem_total_virtual_in_bytes", render.bytes),
        ("open_file_descriptors", "open_file_descriptors", int),
        ("max_file_descriptors", "max_file_descriptors", int),
    ]:
        value, infotext = item_data[data_key]

        yield check_levels(
            value, data_key, params.get(params_key), human_readable_func=hr_func, infoname=infotext
        )


def discover_elasticsearch_nodes(section):
    yield from ((item, {}) for item in section)


check_info["elasticsearch_nodes"] = LegacyCheckDefinition(
    name="elasticsearch_nodes",
    parse_function=parse_elasticsearch_nodes,
    service_name="Elasticsearch Node %s",
    discovery_function=discover_elasticsearch_nodes,
    check_function=check_elasticsearch_nodes,
    check_ruleset_name="elasticsearch_nodes",
    check_default_parameters={"cpu_levels": (75.0, 90.0)},
)
