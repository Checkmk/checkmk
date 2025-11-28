#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    DiscoveryResult,
    InventoryPlugin,
    render,
    Service,
)
from cmk.agent_based.v2 import check_levels as check_levels_v2
from cmk.plugins.azure_v2.agent_based.lib import (
    create_check_metrics_function_single,
    create_inventory_function,
    MetricData,
    parse_resource,
    Resource,
)

agent_section_azure_firewall = AgentSection(
    name="azure_v2_azurefirewalls",
    parse_function=parse_resource,
)

inventory_plugin_azure_firewall = InventoryPlugin(
    name="azure_v2_azurefirewalls",
    inventory_function=create_inventory_function(),
)


def discover_azure_firewall_health(section: Resource) -> DiscoveryResult:
    yield Service()


check_plugin_azure_firewall_health = CheckPlugin(
    name="azure_v2_firewall_health",
    sections=["azure_v2_azurefirewalls"],
    service_name="Azure/Firewall Health",
    discovery_function=discover_azure_firewall_health,
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "average_FirewallHealth",
                "azure_firewall_health",
                "Overall health state",
                render.percent,
                lower_levels_param="health",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_firewall_health",
    check_default_parameters={
        "health": ("fixed", (90.0, 80.0)),
    },
)


def discover_azure_firewall_snat(section: Resource) -> DiscoveryResult:
    yield Service()


check_plugin_azure_firewall_snat = CheckPlugin(
    name="azure_v2_firewall_snat",
    sections=["azure_v2_azurefirewalls"],
    service_name="Azure/Firewall SNAT Utilization",
    discovery_function=discover_azure_firewall_snat,
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "maximum_SNATPortUtilization",
                "azure_firewall_snat_port_utilization",
                "Outbound SNAT port utilization",
                render.percent,
                upper_levels_param="snat_utilization",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_firewall_snat",
    check_default_parameters={
        "snat_utilization": ("fixed", (85.0, 95.0)),
    },
)


def discover_azure_firewall_throughput(section: Resource) -> DiscoveryResult:
    yield Service()


check_plugin_azure_firewall_throughput = CheckPlugin(
    name="azure_v2_firewall_throughput",
    sections=["azure_v2_azurefirewalls"],
    service_name="Azure/Firewall Throughput",
    discovery_function=discover_azure_firewall_throughput,
    check_function=create_check_metrics_function_single(
        [
            MetricData(
                "average_Throughput",
                "azure_firewall_throughput",
                "Throughput",
                render.iobandwidth,
                map_func=lambda x: x / 8,  # we get bits per second from Azure
                upper_levels_param="throughput",
            ),
        ],
        check_levels=check_levels_v2,
    ),
    check_ruleset_name="azure_v2_firewall_throughput",
    check_default_parameters={
        "throughput": ("no_levels", None),
    },
)
