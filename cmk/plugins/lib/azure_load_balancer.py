#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from .azure import FrontendIpConfiguration, Resource


class BackendIpConfiguration(BaseModel):
    name: str
    privateIPAddress: str
    privateIPAllocationMethod: str


class InboundNatRule(BaseModel):
    name: str
    frontendIPConfiguration: Mapping[str, str]
    frontendPort: int
    backendPort: int
    backend_ip_config: BackendIpConfiguration | None = None


class LoadBalancerBackendAddress(BaseModel):
    name: str
    privateIPAddress: str
    privateIPAllocationMethod: str
    primary: bool = False


class LoadBalancerBackendPool(BaseModel):
    id: str
    name: str
    addresses: Sequence[LoadBalancerBackendAddress] = []


class OutboundRule(BaseModel):
    name: str
    protocol: str
    idleTimeoutInMinutes: int
    backendAddressPool: Mapping[str, str]


class LoadBalancer(BaseModel):
    resource: Resource
    name: str
    frontend_ip_configs: Mapping[str, FrontendIpConfiguration]
    inbound_nat_rules: Sequence[InboundNatRule]
    backend_pools: Mapping[str, LoadBalancerBackendPool] = {}
    outbound_rules: Sequence[OutboundRule] = []


Section = Mapping[str, LoadBalancer]
