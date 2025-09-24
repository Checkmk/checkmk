#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

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
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import Host

from ._utils import (
    host_etag,
    PERMISSIONS_UPDATE,
    serialize_host,
    validate_host_attributes_for_quick_setup,
)
from .models.request_models import UpdateHost
from .models.response_models import HostConfigModel


def update_host_v1(
    api_context: ApiContext,
    body: UpdateHost,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_write").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[HostConfigModel]:
    """Update a host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    if api_context.etag.enabled:
        api_context.etag.verify(host_etag(host))

    if not validate_host_attributes_for_quick_setup(host, body):
        raise ProblemException(
            status=400,
            title=f'The host "{host.name()}" is locked by Quick setup.',
            detail="Cannot modify locked attributes.",
        )

    if body.attributes:
        new_attributes = body.attributes.to_internal()
        new_attributes["meta_data"] = host.attributes.get("meta_data", {})
        host.edit(
            new_attributes,
            host.cluster_nodes(),
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

    if body.update_attributes:
        host.update_attributes(
            body.update_attributes.to_internal(),
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

    if body.remove_attributes:
        faulty_attributes = []
        for attribute in body.remove_attributes:
            if attribute not in host.attributes:
                faulty_attributes.append(attribute)

        host.clean_attributes(  # silently ignores missing attributes
            body.remove_attributes,
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

        if faulty_attributes:
            raise ProblemException(
                status=400,
                title="Some attributes were not removed",
                detail=f"The following attributes were not removed since they didn't exist: {', '.join(faulty_attributes)}",
            )

    return ApiResponse(
        body=serialize_host(host, compute_effective_attributes=False, compute_links=True),
        etag=host_etag(host),
    )


ENDPOINT_UPDATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_config", "{host_name}"),
        link_relation=".../update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_UPDATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=update_host_v1)},
    behavior=EndpointBehavior(etag="both"),
)
