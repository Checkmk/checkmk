#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Final
from urllib.parse import urlencode

from cmk.gui.graphing._graph_metric_expressions import GraphConsolidationFunction
from cmk.gui.graphing._html_render import GraphExportRequest
from cmk.gui.graphing.openapi._add_to import parse_specification
from cmk.gui.graphing.openapi._family import GRAPH_FAMILY
from cmk.gui.graphing.openapi.models import ApiConsolidation, ExportRequest, ExportResponse
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

# The legacy pages spell the average out, the API abbreviates it. The translation belongs here, next
# to the legacy type, so that the browser posts the graph in the API's own vocabulary.
_LEGACY_CONSOLIDATION: Final[dict[ApiConsolidation, GraphConsolidationFunction]] = {
    "min": "min",
    "avg": "average",
    "max": "max",
}


def export_v1(body: ExportRequest) -> ExportResponse:
    """Prepare the download of a graph export"""
    # graph_export.py / graph_image.py render the file and answer with it as an attachment. They
    # take the request the legacy "Add to ..." popup builds, which is assembled here so that the
    # browser knows neither that envelope nor how the legacy pages name a consolidation function.
    export_request = GraphExportRequest(
        specification=parse_specification(body.specification),
        consolidation_function=_LEGACY_CONSOLIDATION[body.consolidation_function],
        time_start=body.time_start,
        time_end=body.time_end,
    )
    query = urlencode({"request": json.dumps(export_request.model_dump())})
    return ExportResponse(download_url=f"{body.target}.py?{query}")


ENDPOINT_EXPORT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "export"),
        link_relation="cmk/download",
        method="post",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=export_v1)},
)
