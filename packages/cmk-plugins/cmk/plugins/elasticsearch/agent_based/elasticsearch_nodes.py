#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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


from collections.abc import Callable, Mapping
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
    render,
    Service,
    StringTable,
)

nodes_info = {
    "open_file_descriptors": "Open file descriptors",
    "max_file_descriptors": "Max file descriptors",
    "cpu_percent": "CPU used",
    "cpu_total_in_millis": "CPU total in ms",
    "mem_total_virtual_in_bytes": "Total virtual memory",
}


Section = dict[str, dict[str, tuple[int | float, str]]]


def parse_elasticsearch_nodes(string_table: StringTable) -> Section:
    parsed: Section = {}

    for name, desc, value_str in string_table:
        try:
            value: int | float = float(value_str) if desc == "cpu_percent" else int(value_str)
            parsed.setdefault(name, {}).setdefault(desc, (value, nodes_info[desc]))

        except IndexError, ValueError:
            pass

    return parsed


def check_elasticsearch_nodes(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (item_data := section.get(item)):
        return
    metrics: list[tuple[str, str, Callable[..., Any]]] = [
        ("cpu_percent", "cpu_levels", render.percent),
        ("cpu_total_in_millis", "cpu_total_in_millis", int),
        ("mem_total_virtual_in_bytes", "mem_total_virtual_in_bytes", render.bytes),
        ("open_file_descriptors", "open_file_descriptors", int),
        ("max_file_descriptors", "max_file_descriptors", int),
    ]
    for data_key, params_key, hr_func in metrics:
        value, infotext = item_data[data_key]

        yield from check_levels(
            value, data_key, params.get(params_key), human_readable_func=hr_func, infoname=infotext
        )


def discover_elasticsearch_nodes(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_elasticsearch_nodes = AgentSection(
    name="elasticsearch_nodes",
    parse_function=parse_elasticsearch_nodes,
)


check_plugin_elasticsearch_nodes = CheckPlugin(
    name="elasticsearch_nodes",
    service_name="Elasticsearch Node %s",
    discovery_function=discover_elasticsearch_nodes,
    check_function=check_elasticsearch_nodes,
    check_ruleset_name="elasticsearch_nodes",
    check_default_parameters={"cpu_levels": (75.0, 90.0)},
)
