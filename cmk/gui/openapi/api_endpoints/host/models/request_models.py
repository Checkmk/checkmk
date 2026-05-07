#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import (
    columns_validator,
    query_expression_validator,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables import Hosts
from cmk.livestatus_client.types import Column


@api_model
class ListHostsBody:
    sites: list[Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)]] = (
        api_field(
            description="Restrict the query to this particular site.",
            example=["mysite"],
            default_factory=list,
        )
    )
    query: (
        Annotated[
            QueryExpression,
            query_expression_validator(Hosts, allow_empty=True),
        ]
        | None
    ) = api_field(
        description="An optional Livestatus filter expression to restrict the result set.",
        example='{"op": "!=", "left": "state", "right": "0"}',
        default=None,
    )
    columns: (
        Annotated[
            list[Column],
            columns_validator(Hosts, mandatory=[Hosts.name]),
        ]
        | None
    ) = api_field(
        description="The list of columns to include in the response. The `name` column is always included.",
        example=["name"],
        default=None,
    )
