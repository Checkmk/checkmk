#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import InventoryPlugin, InventoryResult, TableRow
from cmk.plugins.lib.azure import FrontendIpConfiguration
from cmk.plugins.lib.azure_load_balancer import (
    InboundNatRule,
    LoadBalancerBackendPool,
    OutboundRule,
    Section,
)


def iter_inbound_nat_rules(
    rules: Sequence[InboundNatRule],
    frontend_ip_configs: Mapping[str, FrontendIpConfiguration],
    load_balancer: str,
    path: list[str],
) -> InventoryResult:
    for rule in rules:
        yield TableRow(
            path=path + ["inbound_nat_rules"],
            key_columns={"load_balancer": load_balancer, "inbound_nat_rule": rule.name},
            inventory_columns={
                "frontend_port": rule.frontendPort,
                "backend_port": rule.backendPort,
            },
        )

        frontend_ip_config = frontend_ip_configs[rule.frontendIPConfiguration["id"]]
        if (public_ip := frontend_ip_config.public_ip_address) is not None:
            yield TableRow(
                path=path + ["inbound_nat_rules", "public_ips"],
                key_columns={
                    "load_balancer": load_balancer,
                    "inbound_nat_rule": rule.name,
                    "public_ip_name": public_ip.name,
                },
                inventory_columns={
                    "location": public_ip.location,
                    "ip_address": public_ip.ipAddress,
                    "ip_allocation_method": public_ip.publicIPAllocationMethod,
                    "dns_fqdn": public_ip.dns_fqdn,
                },
            )
        else:
            yield TableRow(
                path=path + ["inbound_nat_rules", "private_ips"],
                key_columns={"load_balancer": load_balancer, "inbound_nat_rule": rule.name},
                inventory_columns={
                    "ip_address": frontend_ip_config.privateIPAddress,
                    "ip_allocation_method": frontend_ip_config.privateIPAllocationMethod,
                },
            )

        if (backend_ip_config := rule.backend_ip_config) is not None:
            yield TableRow(
                path=path + ["inbound_nat_rules", "backend_ip_configs"],
                key_columns={
                    "load_balancer": load_balancer,
                    "inbound_nat_rule": rule.name,
                    "backend_ip_config": backend_ip_config.name,
                },
                inventory_columns={
                    "ip_address": backend_ip_config.privateIPAddress,
                    "ip_allocation_method": backend_ip_config.privateIPAllocationMethod,
                },
            )


def iter_outbound_rules(
    rules: Sequence[OutboundRule],
    backend_pools: Mapping[str, LoadBalancerBackendPool],
    load_balancer: str,
    path: list[str],
) -> InventoryResult:
    for rule in rules:
        yield TableRow(
            path=path + ["outbound_rules"],
            key_columns={"load_balancer": load_balancer, "outbound_rule": rule.name},
            inventory_columns={
                "protocol": rule.protocol,
                "idle_timeout": rule.idleTimeoutInMinutes,
            },
        )

        if (backend_pool := backend_pools.get(rule.backendAddressPool["id"])) is None:
            continue

        yield TableRow(
            path=path + ["outbound_rules", "backend_pools"],
            key_columns={
                "load_balancer": load_balancer,
                "outbound_rule": rule.name,
                "backend_pool": backend_pool.name,
            },
        )

        for address in backend_pool.addresses:
            yield TableRow(
                path=path + ["outbound_rules", "backend_pools", "addresses"],
                key_columns={
                    "load_balancer": load_balancer,
                    "outbound_rule": rule.name,
                    "backend_pool": backend_pool.name,
                    "address_name": address.name,
                },
                inventory_columns={
                    "ip_address": address.privateIPAddress,
                    "ip_allocation_method": address.privateIPAllocationMethod,
                    "primary": address.primary,
                },
            )


def inventory_load_balancer(
    section: Section,
) -> InventoryResult:
    path = ["software", "applications", "azure", "load_balancers"]

    for load_balancer in section.values():
        yield TableRow(
            path=path,
            key_columns={
                "name": load_balancer.name,
            },
        )

        yield from iter_inbound_nat_rules(
            load_balancer.inbound_nat_rules,
            load_balancer.frontend_ip_configs,
            load_balancer.name,
            path,
        )

        yield from iter_outbound_rules(
            load_balancer.outbound_rules, load_balancer.backend_pools, load_balancer.name, path
        )


inventory_plugin_azure_load_balancer = InventoryPlugin(
    name="azure_load_balancer",
    sections=["azure_loadbalancers"],
    inventory_function=inventory_load_balancer,
)
