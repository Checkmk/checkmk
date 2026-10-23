#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.hosts_and_folders import Host

from ._family import HOST_CONFIG_FAMILY
from ._utils import make_pending_changes, PERMISSIONS_DELETE


def delete_host_v1(
    api_context: ApiContext,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_read").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[None]:
    """Delete a host"""
    api_context.user.need_permission("wato.edit")
    host.folder().delete_hosts(
        [host.name()],
        automation=delete_hosts,
        pprint_value=api_context.config.wato_pprint_config,
        debug=api_context.config.debug,
        pending_changes=make_pending_changes(api_context),
        acting_user=api_context.user,
    )
    return ApiResponse(body=None, status_code=HTTPStatus.NO_CONTENT)


ENDPOINT_DELETE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_config", "{host_name}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_DELETE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=delete_host_v1)},
)
