#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, assert_never

from pydantic import Discriminator

from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import comment as comment_cmds
from cmk.gui.livestatus_utils.commands.comment import CommentQueryException
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.comment._utils import RW_PERMISSIONS
from cmk.gui.openapi.api_endpoints.comment.models.request_models import (
    CreateServiceCommentModel,
    CreateServiceQueryCommentModel,
)
from cmk.gui.openapi.endpoints import utils
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import ProblemException

from ._family import COMMENT_FAMILY


def create_service_comment_v1(
    body: Annotated[
        CreateServiceCommentModel | CreateServiceQueryCommentModel,
        Discriminator("comment_type"),
    ],
) -> ApiResponse[None]:
    """Create a service comment"""
    user.need_permission("action.addcomment")
    live_connection = sites.live()

    match body:
        case CreateServiceCommentModel():
            site_id = utils.get_site_id_for_host(live_connection, body.host_name)
            comment_cmds.add_service_comment(
                connection=live_connection,
                host_name=body.host_name,
                service_description=body.service_description,
                comment_txt=body.comment,
                site_id=site_id,
                persistent=body.persistent,
                user=user.ident,
            )
        case CreateServiceQueryCommentModel():
            try:
                comment_cmds.add_service_comment_by_query(
                    connection=live_connection,
                    query=body.query,
                    comment_txt=body.comment,
                    persistent=body.persistent,
                    user=user.ident,
                )
            except CommentQueryException:
                raise ProblemException(
                    status=400,
                    title="The query did not match any service names",
                    detail="The provided query returned an empty list so no comment was created",
                )
        case _:
            assert_never(body)

    return ApiResponse(body=None, status_code=204)


ENDPOINT_CREATE_SERVICE_COMMENT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("comment", "service"),
        link_relation="cmk/create_for_service",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=COMMENT_FAMILY.name),
    behavior=EndpointBehavior(update_config_generation=False, skip_locking=True),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=create_service_comment_v1,
        )
    },
)
