#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Comments

In Checkmk you can add comments to hosts and services to store textual information related to the object.
The comments can later be viewed through the user interface or read via API. You could e.g.
add maintenance information about the related host or service to help your colleagues in case problems occur.

The comment endpoints allow for:
* POST creating comments for both hosts and services.
* LIST for getting all host & service comments.
* GET for getting a comment using its ID.
* DELETE for deleting a comment or comments.

Each host or service can have multiple comments.

Related documentation
    https://docs.checkmk.com/latest/en/commands.html#commands


"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from cmk.ccc.site import SiteId

from cmk.utils.livestatus_helpers.expressions import And, Or, QueryExpression
from cmk.utils.livestatus_helpers.tables.comments import Comments

from cmk.gui import fields as gui_fields
from cmk.gui import sites
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands import comment as comment_cmds
from cmk.gui.livestatus_utils.commands.comment import (
    Comment,
    CommentParamException,
    CommentQueryException,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints import utils
from cmk.gui.openapi.endpoints.comment.request_schemas import (
    CreateHostRelatedComment,
    CreateServiceRelatedComment,
    DeleteComments,
)
from cmk.gui.openapi.endpoints.comment.response_schemas import CommentCollection, CommentObject
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import problem, serve_json
from cmk.gui.utils import permission_verification as permissions

from cmk import fields

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
        ]
    )
)

RW_PERMISSIONS = permissions.AllPerm([permissions.Perm("action.addcomment"), PERMISSIONS])


def _serialize_comment(comment: Comment) -> DomainObject:
    dict_comment = dict(comment)

    if "site" in dict_comment:
        dict_comment["site_id"] = dict_comment.pop("site")

    dict_comment["entry_time"] = (
        datetime.strptime(dict_comment["entry_time"], "%b %d %Y %H:%M:%S").isoformat() + "+00:00"
    )

    return constructors.domain_object(
        domain_type="comment",
        identifier=str(comment.id),
        title=comment.comment,
        extensions=dict_comment,
        editable=False,
        deletable=True,
    )


# TODO: verify that the example allows Integer
COMMENT_ID = {
    "comment_id": fields.Integer(
        required=True,
        description="An existing comment's ID",
        example="1",
    )
}

COLLECTION_NAME = {
    "collection_name": fields.String(
        description="Do you want to get comments from 'hosts', 'services' or 'all'",
        enum=["host", "service", "all"],
        example="all",
        required=False,
    )
}

SERVICE_DESCRIPTION_SHOW = {
    "service_description": fields.String(
        description="The service name. No exception is raised when the specified service "
        "description does not exist",
        example="Memory",
        required=False,
    )
}

HOST_NAME_SHOW = {
    "host_name": gui_fields.HostField(
        description="The host name. No exception is raised when the specified host name does not exist",
        should_exist=None,
        example="example.com",
        required=False,
    )
}

SITE_ID = {
    "site_id": gui_fields.SiteField(
        description="An existing site id",
        example="heute",
        presence="should_exist",
        required=True,
    )
}

OPTIONAL_SITE_ID = {
    "site_id": gui_fields.SiteField(
        description="An existing site id",
        example="heute",
        presence="should_exist",
    )
}


class GetCommentsByQuery(BaseSchema):
    query = gui_fields.query_field(
        Comments,
        required=False,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


@Endpoint(
    constructors.object_href("comment", "{comment_id}"),
    "cmk/show",
    method="get",
    tag_group="Monitoring",
    path_params=[COMMENT_ID],
    query_params=[SITE_ID],
    response_schema=CommentObject,
)
def show_comment(params: Mapping[str, Any]) -> Response:
    """Show a comment"""
    try:
        site_id = SiteId(params["site_id"])
        live = sites.live()
        result = (
            comment_cmds.comments_query()
            .filter(Comments.id == params["comment_id"])
            .fetchone(live, True, only_site=site_id)
        )
    except ValueError:
        return problem(
            status=404,
            title="The requested comment was not found",
            detail=f"The comment id {params['comment_id']} did not match any comment.",
        )
    return serve_json(data=_serialize_comment(Comment(**result)))


@Endpoint(
    constructors.collection_href("comment", "{collection_name}"),
    ".../collection",
    method="get",
    tag_group="Monitoring",
    response_schema=CommentCollection,
    update_config_generation=False,
    path_params=[COLLECTION_NAME],
    query_params=[GetCommentsByQuery, HOST_NAME_SHOW, SERVICE_DESCRIPTION_SHOW, OPTIONAL_SITE_ID],
)
def show_comments(params: Mapping[str, Any]) -> Response:
    """Show comments"""

    try:
        sites_to_query = params.get("site_id")
        live = sites.live()
        if sites_to_query:
            live.only_sites = [sites_to_query]

        comments_dict: Mapping[int, Comment] = comment_cmds.get_comments(
            connection=live,
            host_name=params.get("host_name"),
            service_description=params.get("service_description"),
            query=params.get("query"),
            collection_name=comment_cmds.CollectionName[params["collection_name"]],
        )
    except CommentParamException:
        return problem(
            status=400,
            title="Invalid parameter combination",
            detail="You set collection_name to host but the provided filtering parameters will return only service comments.",
        )

    return serve_json(
        constructors.collection_object(
            domain_type="comment",
            value=[_serialize_comment(comment) for _, comment in sorted(comments_dict.items())],
        )
    )


@Endpoint(
    constructors.collection_href("comment", "host"),
    "cmk/create_for_host",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=CreateHostRelatedComment,
    output_empty=True,
    update_config_generation=False,
    permissions_required=RW_PERMISSIONS,
)
def create_host_comment(params: Mapping[str, Any]) -> Response:
    """Create a host comment"""

    user.need_permission("action.addcomment")

    body = params["body"]
    live_connection = sites.live()

    match body["comment_type"]:
        case "host":
            site_id = utils.get_site_id_for_host(live_connection, body["host_name"])
            live_connection.command_obj(
                comment_cmds.AddHostComment(
                    host_name=body["host_name"],
                    user=user.ident,
                    comment=body["comment"],
                    persistent=body["persistent"],
                ),
                site_id,
            )

        case "host_group":
            # TODO
            ...

        case "host_by_query":
            try:
                comment_cmds.add_host_comment_by_query(
                    connection=live_connection,
                    query=body["query"],
                    comment=body["comment"],
                    user=user.ident,
                    persistent=body["persistent"],
                )
            except CommentQueryException:
                return problem(
                    status=400,
                    title="The query did not match any host",
                    detail="The provided query returned an empty list so no comment was created",
                )

    return Response(status=204)


@Endpoint(
    constructors.collection_href("comment", "service"),
    "cmk/create_for_service",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=CreateServiceRelatedComment,
    output_empty=True,
    update_config_generation=False,
    permissions_required=RW_PERMISSIONS,
)
def create_service_comment(params: Mapping[str, Any]) -> Response:
    """Create a service comment"""

    user.need_permission("action.addcomment")

    body = params["body"]
    live_connection = sites.live()

    match body["comment_type"]:
        case "service":
            site_id = utils.get_site_id_for_host(live_connection, body["host_name"])
            comment_cmds.add_service_comment(
                connection=live_connection,
                host_name=body["host_name"],
                service_description=body["service_description"],
                comment_txt=body["comment"],
                site_id=site_id,
                persistent=body["persistent"],
                user=user.ident,
            )

        case "service_group":
            # TODO
            ...

        case "service_by_query":
            try:
                comment_cmds.add_service_comment_by_query(
                    connection=live_connection,
                    query=body["query"],
                    comment_txt=body["comment"],
                    persistent=body["persistent"],
                    user=user.ident,
                )
            except CommentQueryException:
                return problem(
                    status=400,
                    title="The query did not match any service names",
                    detail="The provided query returned an empty list so no comment was created",
                )

    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("comment", "delete"),
    ".../delete",
    method="post",
    tag_group="Monitoring",
    request_schema=DeleteComments,
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_comments(params: Mapping[str, Any]) -> Response:
    """Delete comments"""
    user.need_permission("action.addcomment")
    body = params["body"]

    query_expr: QueryExpression

    site_id: SiteId | None = None
    match body["delete_type"]:
        case "query":
            query_expr = body["query"]

        case "by_id":
            query_expr = Comments.id == body["comment_id"]
            site_id = SiteId(body["site_id"])

        case "params":
            host_name = body["host_name"]
            if body.get("service_descriptions"):
                query_expr = And(
                    Comments.host_name == host_name,
                    Or(
                        *[
                            Comments.service_description == svc_desc
                            for svc_desc in body["service_descriptions"]
                        ]
                    ),
                )
            else:
                query_expr = And(Comments.host_name == host_name)

    comment_cmds.delete_comments(sites.live(), query_expr, site_id)
    return Response(status=204)


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_comment, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_comments, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_host_comment, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_service_comment, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_comments, ignore_duplicates=ignore_duplicates)
