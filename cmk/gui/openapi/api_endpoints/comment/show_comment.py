#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import comment as comment_cmds
from cmk.gui.livestatus_utils.commands.comment import Comment
from cmk.gui.openapi.api_endpoints.comment._utils import PERMISSIONS, serialize_comment
from cmk.gui.openapi.api_endpoints.comment.models.response_models import CommentObjectModel
from cmk.gui.openapi.framework import (
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
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.tables.comments import Comments

from ._family import COMMENT_FAMILY


def show_comment_v1(
    comment_id: Annotated[
        int,
        PathParam(description="An existing comment's ID", example="1"),
    ],
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)],
        QueryParam(description="An existing site id", example="mysite"),
    ],
) -> CommentObjectModel:
    """Show a comment"""
    try:
        live = sites.live()
        result = (
            comment_cmds.comments_query()
            .filter(Comments.id == comment_id)
            .fetchone(live, True, only_site=site_id)
        )
    except ValueError:
        raise ProblemException(
            status=404,
            title="The requested comment was not found",
            detail=f"The comment id {comment_id} did not match any comment.",
        )
    return serialize_comment(Comment(**result))


ENDPOINT_SHOW_COMMENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("comment", "{comment_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=COMMENT_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=show_comment_v1)},
)
