#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow_oneofschema import OneOfSchema  # typing: ignore[attr-defined]

from cmk.fields import String
from cmk.gui.fields import HostField, SiteField
from cmk.gui.openapi.endpoints.metric.common import (
    BaseRequestSchema,
    GraphIdField,
    MetricIdField,
    TYPE_FIELD,
)


class _BaseGetSchema(BaseRequestSchema):
    site = SiteField(
        description="The name of the site. Even though this is optional, specifying a site will greatly improve performance in large distributed systems.",
        example="heute",
    )
    host_name = HostField(
        description="The host name to use.",
        example="my.cool.host",
        should_be_monitored=True,
        should_exist=None,
    )
    service_description = String(
        description="The service, whose data to request.", example="Check_MK", required=True
    )


class _GetOneOfBaseSchema(_BaseGetSchema):
    type = TYPE_FIELD


class GetGraphSchema(_GetOneOfBaseSchema):
    graph_id = GraphIdField()


class GetMetricSchema(_GetOneOfBaseSchema):
    metric_id = MetricIdField()


class GetSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "predefined_graph": GetGraphSchema,
        "single_metric": GetMetricSchema,
    }
