#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""BI aggregation lookups for the Maps SPA.

Thin wrappers around :mod:`cmk.maps.gui._aggregations`, which owns the BIManager
compile/compute pipeline (this layer may not import ``cmk.bi``).
"""

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href, domain_type_action_href
from cmk.maps.gui._aggregations import (
    aggregation_states,
    aggregation_tree,
    AggregationNode,
    list_aggregations,
)
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import (
    MapsAggregationStatesRequest,
    MapsAggregationTreeRequest,
)
from cmk.maps.rest_api.internal.models.response_models import (
    MapsAggregation,
    MapsAggregationNode,
    MapsAggregationsResponse,
    MapsAggregationState,
    MapsAggregationStatesResponse,
    MapsAggregationTreeResponse,
)
from cmk.maps.rest_api.utils import LIVESTATUS_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

_AGGREGATION_PERMISSIONS = permissions.AllPerm(
    [permissions.Perm("maps.use"), *LIVESTATUS_PERMISSIONS]
)


def _to_wire(node: AggregationNode) -> MapsAggregationNode:
    return MapsAggregationNode(
        name=node.name,
        node_type=node.node_type,
        state=node.state,
        in_downtime=node.in_downtime,
        acknowledged=node.acknowledged,
        output=node.output,
        host_name=node.host_name,
        service_description=node.service_description,
        children=[_to_wire(child) for child in node.children],
    )


def list_aggregations_v1() -> MapsAggregationsResponse:
    """Show all BI aggregations"""
    user.need_permission("maps.use")
    return MapsAggregationsResponse(
        aggregations=[
            MapsAggregation(
                aggregation_id=info.aggregation_id,
                title=info.title,
                pack_id=info.pack_id,
                function=info.function,
            )
            for info in list_aggregations()
        ]
    )


def show_aggregation_tree_v1(body: MapsAggregationTreeRequest) -> MapsAggregationTreeResponse:
    """Show one BI aggregation's hierarchy"""
    user.need_permission("maps.use")
    result = aggregation_tree(body.aggregation_id, body.depth)
    return MapsAggregationTreeResponse(
        tree=None if result.tree is None else _to_wire(result.tree),
        connection_ok=result.connection_ok,
    )


def show_aggregation_states_v1(
    body: MapsAggregationStatesRequest,
) -> MapsAggregationStatesResponse:
    """Show the current state of several BI aggregations"""
    user.need_permission("maps.use")
    return MapsAggregationStatesResponse(
        states={
            name: MapsAggregationState(
                state=state.state,
                output=state.output,
                acknowledged=state.acknowledged,
                in_downtime=state.in_downtime,
            )
            for name, state in aggregation_states(body.aggregation_ids).items()
        }
    )


ENDPOINT_LIST_AGGREGATIONS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("maps_aggregation"),
        link_relation="cmk/list_maps_aggregations",
        method="get",
    ),
    permissions=EndpointPermissions(required=_AGGREGATION_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=list_aggregations_v1)},
)

# POST on a read: the SPA polls a whole batch of aggregation names at once, and
# a name is free-form text — too long and too structured for a query string.
ENDPOINT_SHOW_AGGREGATION_TREE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_aggregation", "show-tree"),
        link_relation="cmk/show_maps_aggregation_tree",
        method="post",
    ),
    permissions=EndpointPermissions(required=_AGGREGATION_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_aggregation_tree_v1)},
)

ENDPOINT_SHOW_AGGREGATION_STATES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_aggregation", "show-states"),
        link_relation="cmk/show_maps_aggregation_states",
        method="post",
    ),
    permissions=EndpointPermissions(required=_AGGREGATION_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_aggregation_states_v1)},
)
