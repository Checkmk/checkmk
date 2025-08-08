#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from collections.abc import Mapping
from typing import Any, Dict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    get_value_store,
    render,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS, df_check_filesystem_single
from cmk.plugins.hyperv.lib import parse_hyperv

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_cluster_csv(section: Section) -> DiscoveryResult:
    for csv in section.keys():
        yield Service(item=csv)


def check_hyperv_cluster_csv(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    value_store = get_value_store()
    csv = section.get(item, "")

    if not csv:
        yield Result(state=State(3), summary="CSV not found in agent output")
        return

    mega = 1024.0 * 1024.0
    size_total = int(csv.get("cluster.csv.size")) / mega
    size_avail = int(csv.get("cluster.csv.free_space")) / mega

    if section.get("ignore_levels"):
        message = f"Total size: {render.bytes(size_total)}, Used space is ignored"
        yield Result(state=State(0), summary=message)
    else:
        yield from df_check_filesystem_single(
            value_store,
            item,
            size_total,
            size_avail,
            0,
            None,
            None,
            params=params,
        )


agent_section_hyperv_cluster_csv = AgentSection(
    name="hyperv_cluster_csv",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_cluster_csv = CheckPlugin(
    name="hyperv_cluster_csv",
    service_name="HyperV CSV %s",
    sections=["hyperv_cluster_csv"],
    discovery_function=discovery_hyperv_cluster_csv,
    check_function=check_hyperv_cluster_csv,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
