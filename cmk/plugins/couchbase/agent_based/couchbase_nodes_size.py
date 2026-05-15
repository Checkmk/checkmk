#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def _levels_upper(
    levels: tuple[int, int] | None,
) -> tuple[Literal["fixed"], tuple[int, int]] | None:
    return ("fixed", levels) if levels is not None else None


def discover_couchbase_nodes_size(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _make_check(
    key_disk: str, key_size: str
) -> Callable[[str, Mapping[str, Any], Section], CheckResult]:
    def check(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
        if not (data := section.get(item)):
            return
        on_disk = data.get(key_disk)
        if on_disk is not None:
            yield from check_levels(
                on_disk,
                levels_upper=_levels_upper(params.get("size_on_disk")),
                metric_name="size_on_disk",
                render_func=render.bytes,
                label="Size on disk",
            )

        size = data.get(key_size)
        if size is not None:
            yield from check_levels(
                size,
                levels_upper=_levels_upper(params.get("size")),
                metric_name="data_size",
                render_func=render.bytes,
                label="Data size",
            )

    return check


agent_section_couchbase_nodes_size = AgentSection(
    name="couchbase_nodes_size",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_nodes_size_docs = CheckPlugin(
    name="couchbase_nodes_size_docs",
    service_name="Couchbase %s Documents",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size,
    check_function=_make_check(
        "couch_docs_actual_disk_size",
        "couch_docs_data_size",
    ),
    check_ruleset_name="couchbase_size_docs",
    check_default_parameters={},
)


check_plugin_couchbase_nodes_size_spacial_views = CheckPlugin(
    name="couchbase_nodes_size_spacial_views",
    service_name="Couchbase %s Spacial Views",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size,
    check_function=_make_check(
        "couch_spatial_disk_size",
        "couch_spatial_data_size",
    ),
    check_ruleset_name="couchbase_size_spacial",
    check_default_parameters={},
)


check_plugin_couchbase_nodes_size_couch_views = CheckPlugin(
    name="couchbase_nodes_size_couch_views",
    service_name="Couchbase %s Couch Views",
    sections=["couchbase_nodes_size"],
    discovery_function=discover_couchbase_nodes_size,
    check_function=_make_check(
        "couch_views_actual_disk_size",
        "couch_views_data_size",
    ),
    check_ruleset_name="couchbase_size_couch",
    check_default_parameters={},
)
