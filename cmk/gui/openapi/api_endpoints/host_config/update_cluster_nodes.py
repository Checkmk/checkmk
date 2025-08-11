#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import LinkableModel, LinkModel
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_property_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.watolib.hosts_and_folders import Host

from ._utils import host_etag, PERMISSIONS_UPDATE


@api_model
class UpdateNodes:
    nodes: list[
        Annotated[
            HostName,
            TypedPlainValidator(str, HostConverter(should_be_cluster=False).host_name),
        ]
    ] = api_field(
        description="Nodes where the newly created host should be the cluster-container of.",
        example=["host1", "host2", "host3"],
    )


@api_model
class HostNodesProperty(LinkableModel):
    id: str = api_field(description="The unique name of this property, local to this domain type.")
    value: Sequence[str] = api_field(description="The value of the property. In this case a list.")


def update_cluster_nodes_v1(
    api_context: ApiContext,
    body: UpdateNodes,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_read").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[HostNodesProperty]:
    """Update the nodes of a cluster host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    if api_context.etag.enabled:
        api_context.etag.verify(host_etag(host))

    host.edit(
        host.attributes,
        body.nodes,
        pprint_value=api_context.config.wato_pprint_config,
        use_git=api_context.config.wato_use_git,
    )

    if nodes := host.cluster_nodes():
        value = list(nodes)
    else:
        value = []

    return ApiResponse(
        body=HostNodesProperty(
            id=f"{host.name()}_nodes",
            value=value,
            links=[
                LinkModel.create(
                    rel=".../modify",
                    href=object_property_href("host_config", host.name(), "nodes"),
                    method="put",
                )
            ],
        ),
        etag=host_etag(host),
    )


ENDPOINT_UPDATE_CLUSTER_NODES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_property_href("host_config", "{host_name}", "nodes"),
        link_relation=".../property",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_UPDATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=update_cluster_nodes_v1)},
    behavior=EndpointBehavior(etag="both"),
)
