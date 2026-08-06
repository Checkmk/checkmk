#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client import MKLivestatusException

from .._engine_template_graphs import discover_template_graphs
from .._graph_templates import TemplateGraphSpecification
from ._family import GRAPH_FAMILY
from .models import GraphsDiscoverResponse


@api_model
class TemplateGraphsDiscoverRequest:
    hostname: AnnotatedHostName = api_field(description="The host name.", example="my-host")
    service_description: str = api_field(description="The service description.", example="CPU load")
    graph_id: str | None = api_field(
        description=(
            "Return only the graph with this id. A legacy 'METRIC_<name>' id matches the "
            "single-metric graph of that metric. None returns all graphs of the service."
        ),
        example="cpu_utilization",
        default=None,
    )


def discover_template_graphs_v1(
    body: TemplateGraphsDiscoverRequest,
) -> GraphsDiscoverResponse:
    """Discover the data-less template graph definitions of a service"""
    try:
        discovered = discover_template_graphs(
            TemplateGraphSpecification(
                site=None,
                host_name=body.hostname,
                service_description=body.service_description,
                graph_id=body.graph_id,
            ),
            debug=active_config.debug,
        )
    except MKLivestatusException as exc:
        raise ProblemException(
            status=503,
            title="Monitoring data source unavailable",
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise ProblemException(
            status=500,
            title="Graph discovery failed",
            detail=f"Failed to discover graphs: {exc}",
        ) from exc

    return GraphsDiscoverResponse.from_discovered(discovered)


ENDPOINT_DISCOVER_TEMPLATE_GRAPHS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "discover_template_graphs"),
        link_relation="cmk/discover_template_graphs",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(
            permissions.AllPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=discover_template_graphs_v1)},
)
