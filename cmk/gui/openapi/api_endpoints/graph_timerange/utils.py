#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.type_defs import GraphTimerange
from cmk.gui.utils import permission_verification as permissions

from .models.response_models import (
    GraphTimerangeExtension,
    GraphTimerangeObject,
)

PERMISSIONS = permissions.AllPerm([])


def serialize_graph_timerange(index: int, graph_timerange: GraphTimerange) -> GraphTimerangeObject:
    """Serialize a GraphTimerange object to the API format."""
    return GraphTimerangeObject(
        domainType="graph_timerange",
        id=str(index),
        title=graph_timerange["title"],
        extensions=GraphTimerangeExtension(
            sort_index=index,
            total_seconds=graph_timerange["duration"],
        ),
        links=[LinkModel.create("self", object_href("graph_timerange", "{index}"))],
    )
