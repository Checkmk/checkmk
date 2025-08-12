#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from typing import Annotated

from annotated_types import Ge

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException

from .endpoint_family import GRAPH_TIMERANGE_FAMILY
from .models.response_models import GraphTimerangeObject
from .utils import (
    PERMISSIONS,
    serialize_graph_timerange,
)


def show_graph_timerange_v1(
    api_context: ApiContext,
    index: Annotated[
        int,
        PathParam(
            description="The index used as an identifier.",
            example="1",
        ),
        Ge(0),
    ],
) -> GraphTimerangeObject:
    """Show graph timetrange entry"""
    if index < 0 or index >= len(api_context.config.graph_timeranges):
        raise ProblemException(
            title="Object does not exist",
            detail=f"The graph timerange with the index {index} does not exists.",
            status=HTTPStatus.NOT_FOUND,
        )

    return serialize_graph_timerange(index, api_context.config.graph_timeranges[index])


ENDPOINT_SHOW_GRAPH_TIMERANGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("graph_timerange", "{index}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=GRAPH_TIMERANGE_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=show_graph_timerange_v1)},
)
