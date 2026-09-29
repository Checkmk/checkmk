#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.hosts_and_folders import Host

from ._family import HOST_CONFIG_FAMILY
from ._utils import host_etag, PERMISSIONS, serialize_host
from .models.response_models import HostConfigModel


def show_host_v1(
    api_context: ApiContext,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_read").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
    effective_attributes: Annotated[
        bool,
        QueryParam(
            description="Show all effective attributes on hosts, not just the attributes which were set on "
            "this host specifically. This includes all attributes of all of this host's parent "
            "folders.",
            example="False",
        ),
    ] = False,
) -> ApiResponse[HostConfigModel]:
    """Show a host."""
    return ApiResponse(
        body=serialize_host(
            host,
            api_context=api_context,
            compute_effective_attributes=effective_attributes,
            compute_links=True,
        ),
        status_code=HTTPStatus.OK,
        etag=host_etag(host),
    )


ENDPOINT_SHOW_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_config", "{host_name}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_host_v1)},
    behavior=EndpointBehavior(etag="output"),
)
