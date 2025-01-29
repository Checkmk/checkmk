#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow_oneofschema import OneOfSchema

from cmk.utils.livestatus_helpers import tables

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class CreateCommentBase(BaseSchema):
    comment = fields.String(
        description="The comment which will be stored for the host.",
        example="Windows",
        required=True,
    )

    persistent = fields.Boolean(
        description="If set, the comment will persist a restart.",
        example=False,
        load_default=False,
        required=False,
    )


class CreateHostCommentBase(CreateCommentBase):
    comment_type = fields.String(
        required=True,
        description="How you would like to leave a comment.",
        enum=["host", "host_by_query"],
        example="host",
    )


class CreateHostComment(CreateHostCommentBase):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )


class CreateHostQueryComment(CreateHostCommentBase):
    query = gui_fields.query_field(tables.Hosts, required=False)


class CreateHostRelatedComment(OneOfSchema):
    type_field = "comment_type"
    type_field_remove = False
    type_schemas = {
        "host": CreateHostComment,
        "host_by_query": CreateHostQueryComment,
        # TODO "host_group": CreateHostGroupComment
    }


class CreateServiceCommentBase(CreateCommentBase):
    comment_type = fields.String(
        required=True,
        description="How you would like to leave a comment.",
        enum=["service", "service_by_query"],
        example="service",
    )


class CreateServiceComment(CreateServiceCommentBase):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )
    service_description = fields.String(
        description="The service name for which the comment is for. No exception is raised when the specified service name does not exist",
        example="Memory",
        required=True,
    )


class CreateServiceQueryComment(CreateServiceCommentBase):
    query = gui_fields.query_field(
        tables.Services,
        required=True,
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )


class CreateServiceRelatedComment(OneOfSchema):
    type_field = "comment_type"
    type_field_remove = False
    type_schemas = {
        "service": CreateServiceComment,
        "service_by_query": CreateServiceQueryComment,
        # TODO "service_group": CreateServiceGroupComment
    }


class BaseBulkDelete(BaseSchema):
    delete_type = fields.String(
        required=True,
        description="How you would like to delete comments.",
        enum=["by_id", "query", "params"],
        example="delete_by_query",
    )


class DeleteCommentById(BaseBulkDelete):
    comment_id = fields.Integer(
        required=False,
        description="An integer representing a comment ID.",
        example=21,
    )

    site_id = gui_fields.SiteField(
        description="The ID of an existing site", example="production", required=True
    )


class DeleteCommentsByQuery(BaseBulkDelete):
    query = gui_fields.query_field(
        tables.Comments,
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


class DeleteCommentsByParams(BaseBulkDelete):
    host_name = gui_fields.HostField(
        description="The host name",
        should_exist=True,
        example="example.com",
        required=True,
    )
    service_descriptions = fields.List(
        fields.String(required=False, example="CPU utilization"),
        description="If set, the comments for the listed services of the specified host will be "
        "removed. If a service has multiple comments then all will be removed",
        required=False,
        example=["CPU load", "Memory"],
    )


class DeleteComments(OneOfSchema):
    type_field = "delete_type"
    type_field_remove = False
    type_schemas = {
        "by_id": DeleteCommentById,
        "query": DeleteCommentsByQuery,
        "params": DeleteCommentsByParams,
    }
