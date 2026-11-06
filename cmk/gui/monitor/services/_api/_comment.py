#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus
from typing import Annotated

from annotated_types import MinLen

from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.utils import ProblemException
from cmk.web.utils import permission_verification as permissions

from .._commands import ServiceCommenter
from .._exceptions import ServiceNotFoundError
from .._impl import LiveStatusServiceActions
from .._models import ServiceTarget
from ._family import MONITOR_SERVICES_FAMILY


@api_model
class CommentServiceRef:
    site_id: str = api_field(description="Site ID the service belongs to", example="local")
    host_name: str = api_field(description="Host the service belongs to", example="web-server-01")
    name: str = api_field(description="Service name", example="CPU load")


@api_model
class AddCommentServicesRequestBody:
    services: list[CommentServiceRef] = api_field(description="The services to add the comment to.")
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The comment.", example="Disk swap planned"
    )


@api_model
class AddCommentServicesResponse:
    commented: int = api_field(description="Number of services the comment was added to", example=3)


def add_comment(
    api_context: ApiContext, body: AddCommentServicesRequestBody
) -> AddCommentServicesResponse:
    """Add a comment to the given services."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.addcomment")

    return _handle_add_comment(
        LiveStatusServiceActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_add_comment(
    commenter: ServiceCommenter, body: AddCommentServicesRequestBody, *, author: UserId
) -> AddCommentServicesResponse:
    targets = [
        ServiceTarget(
            site_id=service.site_id, host_name=service.host_name, description=service.name
        )
        for service in body.services
    ]
    count = 0
    if targets:
        try:
            count = commenter.add_comment(targets, author=author, comment=body.comment)
        except ServiceNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the services was found",
                detail="None of the services is monitored on the site given for it.",
            ) from None
    return AddCommentServicesResponse(commented=count)


ENDPOINT_ADD_COMMENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/services/actions/add_comment",
        link_relation="cmk/add_comment",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("general.act"),
                permissions.Perm("action.addcomment"),
                # sites.live() authenticates the user, which checks these permissions.
                permissions.Perm("general.see_all"),
                permissions.OkayToIgnorePerm("bi.see_all"),
                permissions.OkayToIgnorePerm("mkeventd.seeall"),
            ]
        )
    ),
    doc=EndpointDoc(family=MONITOR_SERVICES_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=add_comment)},
)
