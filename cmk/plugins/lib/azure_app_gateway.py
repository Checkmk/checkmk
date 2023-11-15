#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, Field

from .azure import FrontendIpConfiguration, Resource


class FrontendPort(BaseModel):
    port: int


class HttpListener(BaseModel):
    name: str
    frontendIPConfiguration: Mapping[str, str]
    frontendPort: Mapping[str, str]
    protocol: str
    hostNames: Sequence[str]


class BackendHttpSettings(BaseModel):
    name: str
    port: int
    protocol: str


class BackendAddressPool(BaseModel):
    name: str


class RoutingRule(BaseModel):
    name: str
    httpListener: Mapping[str, str]
    # Those are missing for e.g. http redirect rules, see SUP-15950
    backendAddressPool: Mapping[str, str] = {}
    backendHttpSettings: Mapping[str, str] = {}


class AppGateway(BaseModel):
    resource: Resource
    name: str
    operational_state: str
    frontend_api_configs: Mapping[str, FrontendIpConfiguration]
    frontend_ports: Mapping[str, FrontendPort]
    routing_rules: Sequence[RoutingRule]
    http_listeners: Mapping[str, HttpListener]
    backend_settings: Mapping[str, BackendHttpSettings]
    backend_address_pools: Mapping[str, BackendAddressPool]
    waf_enabled: bool | None = Field(None)


Section = Mapping[str, AppGateway]
