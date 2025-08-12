#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import collection_href

from .endpoint_family import GRAPH_TIMERANGE_FAMILY
from .models.response_models import GraphTimerangeCollection
from .utils import PERMISSIONS, serialize_graph_timerange


def list_graph_timerange_v1() -> GraphTimerangeCollection:
    """List all graph timeranges"""

    return GraphTimerangeCollection(
        id="graph_timerange",
        domainType="graph_timerange",
        value=[
            serialize_graph_timerange(index, graph_timerange)
            for index, graph_timerange in enumerate(active_config.graph_timeranges)
        ],
        links=[LinkModel.create("self", collection_href("graph_timerange"))],
    )


ENDPOINT_LIST_GRAPH_TIMERANGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("graph_timerange"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=GRAPH_TIMERANGE_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_graph_timerange_v1)},
)
