#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Annotated

from cmk.ccc.hostaddress import HostName

from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.host_config.models.response_models import HostConfigModel
from cmk.gui.openapi.api_endpoints.host_config.utils import serialize_host
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostUpdateAttributeModel
from cmk.gui.openapi.framework import EndpointBehavior, QueryParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib import bakery
from cmk.gui.watolib.hosts_and_folders import Host


@dataclass(kw_only=True, slots=True)
class CreateHostModel:
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


def create_host_v1(
    body: CreateHostModel,
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
) -> HostConfigModel:
    """Create a hosts."""
    user.need_permission("wato.edit")
    host_name = body.host_name

    # is_cluster is defined as "cluster_hosts is not None"
    body.folder.create_hosts(
        [(host_name, body.attributes.to_internal(), None)],
        pprint_value=active_config.wato_pprint_config,
    )
    if bake_agent:
        bakery.try_bake_agents_for_hosts([host_name], debug=active_config.debug)

    host = Host.load_host(host_name)
    return serialize_host(host, compute_effective_attributes=False, compute_links=True)


ENDPOINT_CREATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("host_config"),
        link_relation="cmk/create",
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
                        ]
                    )
                ),
            ]
        )
    ),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=create_host_v1)},
    behavior=EndpointBehavior(etag="output"),
)
