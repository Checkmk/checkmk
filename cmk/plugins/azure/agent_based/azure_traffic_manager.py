#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    IgnoreResultsError,
    Result,
    State,
)
from cmk.plugins.lib.azure import create_discover_by_metrics_function, parse_resources, Section

agent_section_azure_trafficmanagerprofiles = AgentSection(
    name="azure_trafficmanagerprofiles",
    parse_function=parse_resources,
)


def check_qps(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    resource = section.get(item)
    if resource is None:
        raise IgnoreResultsError("Data not present at the moment")

    metric = resource.metrics.get("total_QpsByEndpoint")
    if metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    queries_per_second = metric.value / 60.0

    yield from check_levels_v1(
        queries_per_second,
        levels_upper=params.get("levels"),
        metric_name="queries_per_sec",
        label="Queries per second",
        render_func=lambda v: str(int(v)),
    )


check_plugin_azure_traffic_manager_qps = CheckPlugin(
    name="azure_traffic_manager_qps",
    sections=["azure_trafficmanagerprofiles"],
    service_name="Azure/Traffic Mgr. %s Qps",
    discovery_function=create_discover_by_metrics_function("total_QpsByEndpoint"),
    check_function=check_qps,
    check_ruleset_name="azure_traffic_manager_qps",
    check_default_parameters={},
)


def check_probe_state(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    resource = section.get(item)
    if resource is None:
        raise IgnoreResultsError("Data not present at the moment")

    metric = resource.metrics.get("maximum_ProbeAgentCurrentEndpointStateByProfileResourceId")
    if metric is None:
        raise IgnoreResultsError("Data not present at the moment")

    if metric.value == 1:
        yield Result(state=State.OK, summary="Probe state: OK")
        return

    not_enabled_state = params.get("custom_state")
    yield Result(state=State(not_enabled_state), summary="Probe state: not OK")


check_plugin_azure_traffic_manager_probe_state = CheckPlugin(
    name="azure_traffic_manager_probe_state",
    sections=["azure_trafficmanagerprofiles"],
    service_name="Azure/Traffic Mgr. %s Probe State",
    discovery_function=create_discover_by_metrics_function(
        "maximum_ProbeAgentCurrentEndpointStateByProfileResourceId"
    ),
    check_function=check_probe_state,
    check_ruleset_name="azure_traffic_manager_probe_state",
    check_default_parameters={"custom_state": 2},
)
