#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric display semantics for the Maps SPA.

Thin wrapper around :mod:`cmk.maps.gui._metrics`, which owns the graphing
pipeline (translations, Perf-O-Meter renderers, graph evaluation).
"""

from cmk.ccc.hostaddress import HostNameValidationError
from cmk.gui.graphing import (
    get_temperature_unit,
    graphs_from_api,
    metrics_from_api,
    perfometers_from_api,
    registered_metrics,
    registered_translations,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.maps.gui._metrics import metric_info, object_context
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsMetricInfoRequest
from cmk.maps.rest_api.internal.models.response_models import (
    MapsGraphGroup,
    MapsMetric,
    MapsMetricInfoResponse,
    MapsMetricUnit,
    MapsMetricUnitPrecision,
    MapsPerfometer,
    MapsPerfometerSegment,
    MapsPerfometerSide,
)
from cmk.maps.rest_api.utils import PERMISSIONS


def show_metric_info_v1(
    body: MapsMetricInfoRequest, api_context: ApiContext
) -> MapsMetricInfoResponse:
    """Resolve raw perfdata against the metric registry"""
    user.need_permission("maps.use")
    # Graph groups are opt-in: the graph evaluation identifies the object, and
    # only graph widgets / the graph picker need them.
    context = None
    if body.graphs:
        if not body.host_name:
            raise ProblemException(
                status=400, title="Missing field", detail="'host_name' is required with 'graphs'."
            )
        try:
            context = object_context(body.site_id, body.host_name, body.service_description)
        except HostNameValidationError:
            raise ProblemException(
                status=400, title="Invalid input", detail="Invalid host name."
            ) from None

    info = metric_info(
        body.perf_data,
        body.check_command,
        registered_metrics=metrics_from_api,
        registered_metric_plugins=registered_metrics(),
        registered_translations=registered_translations(),
        registered_perfometers=perfometers_from_api,
        temperature_unit=get_temperature_unit(user, api_context.config.default_temperature_unit),
        debug=api_context.config.debug,
        registered_graphs=graphs_from_api if context is not None else None,
        object_context=context,
    )

    perfometer = info.perfometer
    return MapsMetricInfoResponse(
        perfometer=(
            None
            if perfometer is None
            else MapsPerfometer(
                label=perfometer.label,
                rows=[
                    [MapsPerfometerSegment(pct=segment.pct, color=segment.color) for segment in row]
                    for row in perfometer.rows
                ],
                sides=[
                    None
                    if side is None
                    else MapsPerfometerSide(title=side.title, label=side.label, pct=side.pct)
                    for side in perfometer.sides
                ],
                bg_color=perfometer.bg_color,
            )
        ),
        metrics={
            label: MapsMetric(
                name=metric.name,
                title=metric.title,
                scale=metric.scale,
                unit=MapsMetricUnit(
                    notation=metric.unit.notation,
                    symbol=metric.unit.symbol,
                    precision=MapsMetricUnitPrecision(
                        type=metric.unit.precision.type,
                        digits=metric.unit.precision.digits,
                    ),
                ),
                color=metric.color,
            )
            for label, metric in info.metrics.items()
        },
        graphs=(
            ApiOmitted()
            if info.graphs is None
            else [
                MapsGraphGroup(
                    graph_id=group.graph_id,
                    title=group.title,
                    metrics=group.metrics,
                    mirrored=group.mirrored,
                )
                for group in info.graphs
            ]
        ),
    )


# POST on a read: the perfdata string is free-form and can be several kilobytes
# on a wide check — too long for a query string.
ENDPOINT_SHOW_METRIC_INFO = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_metric_info", "resolve"),
        link_relation="cmk/show_maps_metric_info",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_metric_info_v1)},
)
