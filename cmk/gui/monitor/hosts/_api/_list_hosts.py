#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal

from cmk.gui.openapi.framework import QueryParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)

from ._family import MONITOR_HOSTS_FAMILY


@api_model
class HostEntry:
    name: str = api_field(description="Host name", example="web-server-01")
    state: Literal["UP", "DOWN", "UNREACHABLE"] = api_field(description="Host state", example="UP")
    ip: str = api_field(description="Primary IP address", example="10.0.0.1")
    alias: str = api_field(description="Host alias", example="Web Server")
    num_services_ok: int = api_field(description="Number of services in OK state", example=42)
    num_services_warn: int = api_field(description="Number of services in WARNING state", example=3)
    num_services_crit: int = api_field(
        description="Number of services in CRITICAL state", example=1
    )
    num_services_unknown: int = api_field(
        description="Number of services in UNKNOWN state", example=0
    )
    num_services_pending: int = api_field(
        description="Number of services in PENDING state", example=2
    )


@api_model
class HostsPageMeta:
    limit: int = api_field(description="Requested page size", example=1000)
    total: int = api_field(description="Total number of hosts", example=1234)


@api_model
class HostsResponse:
    hosts: list[HostEntry] = api_field(description="The hosts for this query", example=[])
    meta: HostsPageMeta = api_field(description="Page metadata")


def list_hosts(
    limit: Annotated[
        int,
        QueryParam(description="Number of hosts to return", example="1000"),
    ] = 1000,
) -> HostsResponse:
    """
    Returns a list of hosts with their current state and some basic information.
    """
    return HostsResponse(
        hosts=[],
        meta=HostsPageMeta(limit=limit, total=0),
    )


# export endpoint
ENDPOINT_LIST_HOSTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="monitor/hosts",
        # TODO: need to determine what the link relation should be.
        link_relation="cmk/list",
        method="get",
    ),
    # TODO: need to actually provide some permissions here.
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_hosts)},
)
