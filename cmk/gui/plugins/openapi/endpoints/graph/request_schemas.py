#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.fields import HostField, SiteField
from cmk.gui.fields.base import BaseSchema
from cmk.gui.plugins.openapi.endpoints.graph.common import (
    BaseRequestSchema,
    GRAPH_NAME_REGEX,
    GRAPH_NAME_VALIDATOR,
)

from cmk.fields import Nested, String


class _MetricSpec(BaseSchema):
    site = SiteField(description="The name of the site.", example="heute", required=True)
    host_name = HostField(description="The hostname to use.", example="my.cool.host", required=True)
    service = String(
        description="The service, whose data to request.", example="Memory", required=True
    )
    metric_name = String(
        description=f"The name of the requested metric. Must match pattern {GRAPH_NAME_REGEX}.",
        example="apache_state_logging",
        required=True,
        validate=GRAPH_NAME_VALIDATOR,
    )


class MetricSchema(BaseRequestSchema):
    spec = Nested(
        _MetricSpec,
        description="The specification of a metric graph.",
        required=True,
        example={
            "site": "heute",
            "host_name": "my.cool.host",
            "service": "Memory",
            "metric_name": "some_metric_here",
        },
    )
