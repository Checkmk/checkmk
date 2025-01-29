#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection

from cmk import fields


class CommentAttributes(BaseSchema):
    host_name = fields.String(required=True, description="The host name.")

    id = fields.Integer(
        required=True,
        description="The comment ID",
    )
    author = fields.String(
        required=True,
        description="The author of the comment",
    )
    comment = fields.String(required=True, description="The comment itself")

    persistent = fields.Boolean(required=True, description="If true, the comment will be persisted")

    entry_time = fields.String(
        required=True, description="The timestamp from when the comment was created."
    )
    service_description = fields.String(
        required=False, description="The service name the comment belongs to."
    )
    is_service = fields.Boolean(
        required=True, description="True if the comment is from a service or else it's False."
    )

    site_id = fields.String(
        description="The site id of the downtime.",
        example="production",
        required=True,
    )


class CommentObject(DomainObject):
    domainType = fields.Constant(
        "comment",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        CommentAttributes, description="The attributes of a service/host comment."
    )


class CommentCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "comment",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(CommentObject),
        description="A list of comment objects.",
    )
