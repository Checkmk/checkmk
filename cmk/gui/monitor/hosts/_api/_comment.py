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

from .._commands import HostCommenter
from .._exceptions import HostNotFoundError
from .._impl import LiveStatusHostActions
from .._models import HostTarget
from ._family import MONITOR_HOSTS_FAMILY


@api_model
class CommentHostRef:
    site_id: str = api_field(description="Site ID the host belongs to", example="local")
    name: str = api_field(description="Host name", example="web-server-01")


@api_model
class AddCommentRequestBody:
    hosts: list[CommentHostRef] = api_field(description="The hosts to add the comment to.")
    comment: Annotated[str, MinLen(1)] = api_field(
        description="The comment.", example="Disk swap planned"
    )


@api_model
class AddCommentResponse:
    commented: int = api_field(description="Number of hosts the comment was added to", example=3)


def add_comment(api_context: ApiContext, body: AddCommentRequestBody) -> AddCommentResponse:
    """Add a comment to the given hosts."""
    api_context.user.need_permission("general.act")
    api_context.user.need_permission("action.addcomment")

    return _handle_add_comment(
        LiveStatusHostActions(connection=sites.live()), body, author=api_context.user.ident
    )


def _handle_add_comment(
    commenter: HostCommenter, body: AddCommentRequestBody, *, author: UserId
) -> AddCommentResponse:
    targets = [HostTarget(site_id=host.site_id, host_name=host.name) for host in body.hosts]
    count = 0
    if targets:
        try:
            count = commenter.add_comment(targets, author=author, comment=body.comment)
        except HostNotFoundError:
            raise ProblemException(
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                title="None of the hosts was found",
                detail="None of the hosts is monitored on the site given for it.",
            ) from None
    return AddCommentResponse(commented=count)


ENDPOINT_ADD_COMMENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/monitor/hosts/actions/add_comment",
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
    doc=EndpointDoc(family=MONITOR_HOSTS_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=add_comment)},
)
