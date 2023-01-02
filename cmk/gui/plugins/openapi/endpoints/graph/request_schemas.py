#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow_oneofschema import OneOfSchema

from cmk.gui.fields import HostField, SiteField
from cmk.gui.plugins.openapi.endpoints.graph.common import BaseRequestSchema, GRAPH_NAME_VALIDATOR

from cmk.fields import String


class _BaseGetSchema(BaseRequestSchema):
    type = String(enum=["graph", "metric"], example="metric", required=True)
    site = SiteField(description="The name of the site.", example="heute", required=True)
    host_name = HostField(
        description="The hostname to use.",
        example="my.cool.host",
        should_be_monitored=True,
        should_exist=None,
    )
    service_description = String(
        description="The service, whose data to request.", example="Check_MK", required=True
    )


class GetGraphSchema(_BaseGetSchema):
    graph_name = String(
        description="The name of the graph.",
        example="cmk_cpu_time_by_phase",
        required=True,
        validate=GRAPH_NAME_VALIDATOR,
    )


class GetMetricSchema(_BaseGetSchema):
    metric_name = String(
        description="The name of the metric.",
        example="cmk_time_agent",
        required=True,
        validate=GRAPH_NAME_VALIDATOR,
    )


class GetSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "graph": GetGraphSchema,
        "metric": GetMetricSchema,
    }
