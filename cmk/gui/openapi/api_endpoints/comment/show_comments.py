#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.livestatus_utils.commands import comment as comment_cmds
from cmk.gui.livestatus_utils.commands.comment import CommentParamException
from cmk.gui.openapi.api_endpoints.comment._utils import PERMISSIONS, serialize_comment
from cmk.gui.openapi.api_endpoints.comment.models.response_models import CommentCollectionModel
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
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.framework.model.common_fields import (
    AnnotatedHostName,
    query_expression_validator,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables.comments import Comments

from ._family import COMMENT_FAMILY


def show_comments_v1(
    api_context: ApiContext,
    collection_name: Annotated[
        Literal["host", "service", "all"],
        PathParam(
            description="Do you want to get comments from 'hosts', 'services' or 'all'",
            example="all",
        ),
    ],
    query: Annotated[
        Annotated[QueryExpression, query_expression_validator(Comments, allow_empty=True)] | None,
        QueryParam(
            description="A Livestatus filter expression for comments.",
            example='{"op": "=", "left": "host_name", "right": "example.com"}',
        ),
    ] = None,
    host_name: Annotated[
        AnnotatedHostName | None,
        QueryParam(
            description="The host name. No exception is raised when the specified host name does not exist",
            example="example.com",
        ),
    ] = None,
    service_description: Annotated[
        str | None,
        QueryParam(
            description="The service name. No exception is raised when the specified service "
            "description does not exist",
            example="Memory",
        ),
    ] = None,
    site_id: Annotated[
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)] | None,
        QueryParam(
            description="An existing site id",
            example="mysite",
        ),
    ] = None,
) -> CommentCollectionModel:
    """Show comments"""
    try:
        live = sites.live()
        if site_id is not None:
            live.only_sites = [site_id]

        comments_dict = comment_cmds.get_comments(
            connection=live,
            host_name=str(host_name) if host_name is not None else None,
            service_description=service_description,
            query=query,
            collection_name=comment_cmds.CollectionName[collection_name],
        )
    except CommentParamException:
        raise ProblemException(
            status=400,
            title="Invalid parameter combination",
            detail="You set collection_name to host but the provided filtering parameters will return only service comments.",
        )

    return CommentCollectionModel(
        id="comment",
        domainType="comment",
        links=[
            link_to_endpoint(
                family=COMMENT_FAMILY.name,
                link_relation=".../collection",
                version=APIVersion.V1,
                host_url=api_context.host_url,
                parameters={"collection_name": collection_name},
                as_self=True,
            )
        ],
        value=[serialize_comment(comment) for _, comment in sorted(comments_dict.items())],
        extensions={},
    )


ENDPOINT_SHOW_COMMENTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("comment", "{collection_name}"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=COMMENT_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True),
    versions={APIVersion.V1: EndpointHandler(handler=show_comments_v1)},
)
