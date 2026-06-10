#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import comment as comment_cmds
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.comment._utils import RW_PERMISSIONS
from cmk.gui.openapi.api_endpoints.comment.models.request_models import (
    DeleteCommentByIdModel,
    DeleteCommentsByParamsModel,
    DeleteCommentsByQueryModel,
)
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.framework.versioned_endpoint import EndpointBehavior
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.livestatus_client.expressions import And, Or, QueryExpression
from cmk.livestatus_client.tables.comments import Comments

from ._family import COMMENT_FAMILY


def delete_comments_v1(
    body: Annotated[
        DeleteCommentByIdModel | DeleteCommentsByQueryModel | DeleteCommentsByParamsModel,
        Discriminator("delete_type"),
    ],
) -> ApiResponse[None]:
    """Delete comments"""
    user.need_permission("action.addcomment")

    query_expr: QueryExpression
    site_id: SiteId | None = None

    match body:
        case DeleteCommentsByQueryModel():
            query_expr = body.query
        case DeleteCommentByIdModel():
            query_expr = Comments.id.equals(body.comment_id)
            site_id = body.site_id
        case DeleteCommentsByParamsModel():
            host_name = body.host_name
            if body.service_descriptions:
                query_expr = And(
                    Comments.host_name == host_name,
                    Or(
                        *[
                            Comments.service_description == svc_desc
                            for svc_desc in body.service_descriptions
                        ]
                    ),
                )
            else:
                query_expr = And(Comments.host_name == host_name)
        case _:
            assert_never(body)

    comment_cmds.delete_comments(sites.live(), query_expr, site_id)
    return ApiResponse(body=None, status_code=204)


ENDPOINT_DELETE_COMMENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("comment", "delete"),
        link_relation=".../delete",
        method="post",
        content_type=None,
    ),
    behavior=EndpointBehavior(update_config_generation=False, skip_locking=True),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=COMMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=delete_comments_v1)},
)
