#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.openapi.api_endpoints.host_config.models.response_models import (
    HostConfigModel,
)
from cmk.gui.openapi.api_endpoints.host_config.utils import serialize_host
from cmk.gui.openapi.framework import EndpointBehavior, PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.hosts_and_folders import Host


def show_host_v1(
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_read").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> HostConfigModel:
    """Show a host."""
    return serialize_host(host, compute_effective_attributes=False, compute_links=True)


ENDPOINT_SHOW_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_config", "{host_name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(permissions.Perm("wato.see_all_folders"))
    ),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_host_v1)},
    behavior=EndpointBehavior(etag="output"),
)
