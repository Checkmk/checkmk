#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.exceptions import MKAuthException
from cmk.gui.openapi.endpoints.utils import folder_slug
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
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.web.utils import permission_verification as permissions

from ._family import HOST_CONFIG_FAMILY
from ._utils import host_etag, make_pending_changes, rw_permissions, serialize_host
from .models.response_models import HostConfigModel

PERMISSIONS_MOVE = rw_permissions(
    permissions.Perm("wato.edit"),
    permissions.Perm("wato.edit_hosts"),
    permissions.Perm("wato.move_hosts"),
    permissions.Perm("wato.manage_hosts"),
)


@api_model
class MoveHostModel:
    target_folder: AnnotatedFolder = api_field(
        description="The path of the target folder where the host is supposed to be moved to.",
        example="/my/fine/folder",
    )


def move_host_v1(
    api_context: ApiContext,
    body: MoveHostModel,
    host: Annotated[
        Annotated[
            # The move permission is enforced by the handler (via choices_for_moving_host -> 403);
            # the path param only needs to load the host.
            Host,
            TypedPlainValidator(str, HostConverter().host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[HostConfigModel]:
    """Move a host to another folder"""
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.move_hosts")
    if api_context.etag.enabled:
        api_context.etag.verify(host_etag(host))
    current_folder = host.folder()
    target_folder = body.target_folder

    if target_folder is current_folder:
        raise ProblemException(
            status=400,
            title="Invalid move action",
            detail="The host is already part of the specified target folder",
        )
    try:
        if target_folder.as_choice_for_moving() not in current_folder.choices_for_moving_host(
            api_context.user
        ):
            raise MKAuthException
        current_folder.move_hosts(
            [host.name()],
            target_folder,
            pprint_value=api_context.config.wato_pprint_config,
            pending_changes=make_pending_changes(api_context),
            acting_user=api_context.user,
        )
    except MKAuthException:
        raise ProblemException(
            status=403,
            title="Permission denied",
            detail=f"You lack the permissions to move host {host.name()} to {folder_slug(target_folder)}.",
        )

    return ApiResponse(
        body=serialize_host(
            host, api_context=api_context, compute_effective_attributes=False, compute_links=True
        ),
        status_code=200,
        etag=host_etag(host),
    )


ENDPOINT_MOVE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("host_config", "{host_name}", action_name="move"),
        link_relation="cmk/move",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_MOVE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=move_host_v1,
            additional_status_codes=[403],
            status_descriptions={
                403: "You lack the permissions to move the host to the target folder.",
            },
        )
    },
    behavior=EndpointBehavior(etag="both"),
)
