#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from .._frontend import load_graph_pin
from ._family import GRAPH_FAMILY


@api_model
class GetGraphPinResponse:
    pin_time: int | None = api_field(
        description=(
            "The timestamp (epoch seconds) marked on the graphs, or null when no pin is set. "
            "The pin is a single per-user marker shared by all of the user's graphs."
        ),
        example=1700000000,
    )


def get_graph_pin_v1(api_context: ApiContext) -> GetGraphPinResponse:
    """Show the graph pin"""
    return GetGraphPinResponse(pin_time=load_graph_pin(api_context.user))


ENDPOINT_GET_GRAPH_PIN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "get_pin"),
        link_relation=".../property",
        method="get",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=get_graph_pin_v1)},
)
