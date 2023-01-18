#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, register, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.azure import FrontendIpConfiguration
from cmk.base.plugins.agent_based.utils.azure_load_balancer import (
    InboundNatRule,
    LoadBalancerBackendPool,
    OutboundRule,
    Section,
)


def iter_inbound_nat_rules(
    rules: Sequence[InboundNatRule],
    frontend_ip_configs: Mapping[str, FrontendIpConfiguration],
    path: list[str],
) -> InventoryResult:
    for rule in rules:
        yield Attributes(
            path=path + ["inbound_nat_rules", rule.name],
            inventory_attributes={
                "name": rule.name,
                "frontend_port": rule.frontendPort,
                "backend_port": rule.backendPort,
            },
        )

        frontend_ip_config = frontend_ip_configs[rule.frontendIPConfiguration["id"]]
        if (public_ip := frontend_ip_config.public_ip_address) is not None:
            yield Attributes(
                path=path + ["inbound_nat_rules", rule.name, "public_ip"],
                inventory_attributes={
                    "name": public_ip.name,
                    "location": public_ip.location,
                    "ip_address": public_ip.ipAddress,
                    "ip_allocation_method": public_ip.publicIPAllocationMethod,
                    "dns_fqdn": public_ip.dns_fqdn,
                },
            )
        else:
            yield Attributes(
                path=path + ["inbound_nat_rules", rule.name, "private_ip"],
                inventory_attributes={
                    "ip_address": frontend_ip_config.privateIPAddress,
                    "allocation_method": frontend_ip_config.privateIPAllocationMethod,
                },
            )

        if (backend_ip_config := rule.backend_ip_config) is not None:
            yield Attributes(
                path=path + ["inbound_nat_rules", rule.name, "backend_ip_config"],
                inventory_attributes={
                    "name": backend_ip_config.name,
                    "ip_address": backend_ip_config.privateIPAddress,
                    "ip_allocation_method": backend_ip_config.privateIPAllocationMethod,
                },
            )


def iter_outbound_rules(
    rules: Sequence[OutboundRule],
    backend_pools: Mapping[str, LoadBalancerBackendPool],
    path: list[str],
) -> InventoryResult:
    for rule in rules:
        yield Attributes(
            path=path + ["outbound_rules", rule.name],
            inventory_attributes={
                "name": rule.name,
                "protocol": rule.protocol,
                "idle_timeout": rule.idleTimeoutInMinutes,
            },
        )

        backend_pool = backend_pools[rule.backendAddressPool["id"]]
        yield Attributes(
            path=path + ["outbound_rules", rule.name, "backend_pool"],
            inventory_attributes={"name": backend_pool.name},
        )

        for address in backend_pool.addresses:
            yield TableRow(
                path=path + ["outbound_rules", rule.name, "backend_pool", "addresses"],
                key_columns={
                    "name": address.name,
                    "ip_address": address.privateIPAddress,
                    "ip_allocation_method": address.privateIPAllocationMethod,
                    "primary": address.primary,
                },
            )


def inventory_load_balancer(
    section: Section,
) -> InventoryResult:
    path = ["azure", "services", "load_balancer"]

    for load_balancer in section.values():
        yield TableRow(
            path=path,
            key_columns={
                "object": "resource",
                "name": load_balancer.name,
            },
        )

        yield from iter_inbound_nat_rules(
            load_balancer.inbound_nat_rules,
            load_balancer.frontend_ip_configs,
            path + [load_balancer.name],
        )

        yield from iter_outbound_rules(
            load_balancer.outbound_rules, load_balancer.backend_pools, path + [load_balancer.name]
        )


register.inventory_plugin(
    name="azure_load_balancer",
    sections=["azure_loadbalancers"],
    inventory_function=inventory_load_balancer,
)
