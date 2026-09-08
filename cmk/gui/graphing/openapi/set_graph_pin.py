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

from .._frontend import save_graph_pin
from ._family import GRAPH_FAMILY


@api_model
class SetGraphPinRequest:
    pin_time: int | None = api_field(
        description=(
            "The timestamp (epoch seconds) to mark on the graphs, or null to remove the pin. "
            "The pin is a single per-user marker shared by all of the user's graphs."
        ),
        example=1700000000,
    )


def set_graph_pin_v1(api_context: ApiContext, body: SetGraphPinRequest) -> None:
    """Set or remove the graph pin"""
    save_graph_pin(api_context.user, body.pin_time)


ENDPOINT_SET_GRAPH_PIN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "set_pin"),
        link_relation="cmk/update",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=set_graph_pin_v1)},
)
