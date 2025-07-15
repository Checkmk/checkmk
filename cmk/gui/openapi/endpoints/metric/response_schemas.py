#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.fields import Float, Integer, List, Nested, String
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.endpoints.metric.common import TimeRange


class MetricSchema(BaseSchema):
    color = String(
        description="The color of the metric as displayed in Checkmk. Color is in HTML notation.",
        example="#80ff40",
    )
    data_points = List(
        Float(),
        description="The samples of the metric.",
        required=True,
        example=[
            3752390000.0,
            3746380000.0,
            3770930000.0,
            3773230000.0,
            3796020000.0,
            3787010000.0,
            3777880000.0,
            3781040000.0,
            3798920000.0,
            3805910000.0,
        ],
    )
    # TODO: add enum if possible
    line_type = String(description="The line type to use.", example="area", required=True)
    title = String(description="The title of the graph.", example="RAM used", required=True)


class GraphCollectionSchema(BaseSchema):
    time_range = Nested(
        TimeRange,
        description="The time range within the samples of the response lie.",
        required=True,
        example={"time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"}},
    )
    # Not sure about the unit here
    step = Integer(
        description="The interval between two samples in seconds.", example=60, required=True
    )
    metrics = Nested(
        MetricSchema,
        description="The actual graph data.",
        required=True,
        many=True,
        example=[
            {
                "color": "#ffffff",
                "data_points": [1.0, 2.0, 3.0, 1.0],
                "line_type": "area",
                "title": "RAM used",
            }
        ],
    )
