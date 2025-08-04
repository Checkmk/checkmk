#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostUpdateAttributeModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib import bakery
from cmk.gui.watolib.hosts_and_folders import Host

from ._utils import host_etag, serialize_host
from .models.response_models import HostConfigModel


@api_model
class CreateClusterHostModel:
    host_name: Annotated[HostName, TypedPlainValidator(str, HostConverter.not_exists)] = api_field(
        description="The hostname or IP address of the host to be created.",
    )
    folder: AnnotatedFolder = api_field(
        description="The path name of the folder.",
        example="/folder/subfolder",
    )
    attributes: HostUpdateAttributeModel = api_field(
        default_factory=lambda: HostUpdateAttributeModel(dynamic_fields={}),
        description="Attributes to set on the newly created host. You can specify custom attributes and tag groups in addition to the built-in ones listed below.",
        example={"ipaddress": "192.168.0.123"},
    )
    nodes: Annotated[list[HostName], TypedPlainValidator(list, HostConverter.host_name)] = (
        api_field(
            description="Nodes where the newly created host should be the cluster-container of.",
            example=["host1", "host2", "host3"],
        )
    )


def create_cluster_host_v1(
    api_context: ApiContext,
    body: CreateClusterHostModel,
    bake_agent: Annotated[
        bool,
        QueryParam(
            description=(
                "Tries to bake the agents for the just created hosts. This process is started in the "
                "background after configuring the host. Please note that the backing may take some "
                "time and might block subsequent API calls. "
                "This only works when using the Enterprise Editions."
            ),
            example="True",
        ),
    ] = False,
) -> ApiResponse[HostConfigModel]:
    """Create a cluster host

    A cluster host groups many hosts (called nodes in this context) into a conceptual cluster.
    All the services of the individual nodes will be collated on the cluster host."""
    user.need_permission("wato.edit")
    host_name = body.host_name

    body.folder.create_hosts(
        [(host_name, body.attributes.to_internal(), body.nodes)],
        pprint_value=api_context.config.wato_pprint_config,
        use_git=api_context.config.wato_use_git,
    )
    if bake_agent:
        bakery.try_bake_agents_for_hosts([host_name], debug=api_context.config.debug)

    host = Host.load_host(host_name)
    return ApiResponse(
        serialize_host(host, compute_effective_attributes=False, compute_links=True),
        etag=host_etag(host),
    )


ENDPOINT_CREATE_CLUSTER_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("host_config", "clusters"),
        link_relation="cmk/create_cluster",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("wato.edit"),
                permissions.Perm("wato.manage_hosts"),
                permissions.Optional(permissions.Perm("wato.all_folders")),
                permissions.Undocumented(
                    permissions.AnyPerm(
                        [
                            permissions.OkayToIgnorePerm("bi.see_all"),
                            permissions.Perm("general.see_all"),
                            permissions.OkayToIgnorePerm("mkeventd.seeall"),
                            # only used to check if user can see a host
                            permissions.Perm("wato.see_all_folders"),
                        ]
                    )
                ),
            ]
        )
    ),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=create_cluster_host_v1)},
    behavior=EndpointBehavior(etag="output"),
)
