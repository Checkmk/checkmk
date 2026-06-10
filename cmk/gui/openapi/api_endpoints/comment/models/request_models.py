#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import query_expression_validator
from cmk.gui.openapi.framework.model.converter import (
    HostConverter,
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables import Hosts, Services
from cmk.livestatus_client.tables.comments import Comments


@api_model
class _CreateCommentBase:
    comment: str = api_field(
        description="The comment which will be stored for the host.",
        example="Windows",
    )
    persistent: bool = api_field(
        description="If set, the comment will persist a restart.",
        example=False,
        default=False,
    )


@api_model
class CreateHostCommentModel(_CreateCommentBase):
    comment_type: Literal["host"] = api_field(
        description="How you would like to leave a comment.",
        example="host",
    )
    host_name: Annotated[HostName, TypedPlainValidator(str, HostConverter().host_name)] = api_field(
        description="The host name",
        example="example.com",
    )


@api_model
class CreateHostQueryCommentModel(_CreateCommentBase):
    comment_type: Literal["host_by_query"] = api_field(
        description="How you would like to leave a comment.",
        example="host_by_query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Hosts, allow_empty=True)] = (
        api_field(
            description="A Livestatus filter expression for hosts.",
            example='{"op": "=", "left": "name", "right": "example.com"}',
        )
    )


@api_model
class CreateServiceCommentModel(_CreateCommentBase):
    comment_type: Literal["service"] = api_field(
        description="How you would like to leave a comment.",
        example="service",
    )
    host_name: Annotated[HostName, TypedPlainValidator(str, HostConverter().host_name)] = api_field(
        description="The host name",
        example="example.com",
    )
    service_description: str = api_field(
        description="The service name for which the comment is for. No exception is raised when the specified service name does not exist",
        example="Memory",
    )


@api_model
class CreateServiceQueryCommentModel(_CreateCommentBase):
    comment_type: Literal["service_by_query"] = api_field(
        description="How you would like to leave a comment.",
        example="service_by_query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Services)] = api_field(
        description="A Livestatus filter expression for services.",
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )


@api_model
class DeleteCommentByIdModel:
    delete_type: Literal["by_id"] = api_field(
        description="How you would like to delete comments.",
        example="by_id",
    )
    comment_id: int = api_field(
        description="An integer representing a comment ID.",
        example=21,
    )
    site_id: Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)] = api_field(
        description="The ID of an existing site",
        example="production",
    )


@api_model
class DeleteCommentsByQueryModel:
    delete_type: Literal["query"] = api_field(
        description="How you would like to delete comments.",
        example="query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Comments)] = api_field(
        description="A Livestatus filter expression for comments.",
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


@api_model
class DeleteCommentsByParamsModel:
    delete_type: Literal["params"] = api_field(
        description="How you would like to delete comments.",
        example="params",
    )
    host_name: Annotated[HostName, TypedPlainValidator(str, HostConverter().host_name)] = api_field(
        description="The host name",
        example="example.com",
    )
    service_descriptions: list[str] | None = api_field(
        description="If set, the comments for the listed services of the specified host will be "
        "removed. If a service has multiple comments then all will be removed",
        example=["CPU load", "Memory"],
        default=None,
    )
