#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from datetime import datetime, timedelta
from typing import Any

import marshmallow

from cmk.fields import Nested, String
from cmk.gui.fields import Timestamp
from cmk.gui.fields.base import BaseSchema

GRAPH_NAME_REGEX = r"^\w[_\-\w\d\.]*$"
GRAPH_NAME_ERROR_MESSAGE = "{input} is not a valid value for this field. It must match the pattern {regex} and contain only ASCII characters."
GRAPH_NAME_VALIDATOR = marshmallow.validate.Regexp(
    regex=GRAPH_NAME_REGEX, error=GRAPH_NAME_ERROR_MESSAGE, flags=re.ASCII
)

TYPE_FIELD = String(
    enum=["predefined_graph", "single_metric"],
    example="single_metric",
    required=True,
    description=(
        "Specify whether you want to receive a single metric (via metric_id), "
        "or a predefined graph containing multiple metrics (via graph_id)."
    ),
)


class GraphIdField(String):
    def __init__(self):
        super().__init__(
            description=(
                "The ID of the predefined graph. "
                'After activating the "Show internal IDs" in the "display '
                'options" of the Service view, you can see the ID of a '
                "predefined graph in the title of the graph."
            ),
            example="cmk_cpu_time_by_phase",
            required=True,
            validate=GRAPH_NAME_VALIDATOR,
        )


class MetricIdField(String):
    def __init__(self):
        super().__init__(
            description=(
                "The ID of the single metric."
                'After activating the "Show internal IDs" in the "display '
                'options" of the Service view, you can see the ID of a '
                "single metric in the legend of the graph."
            ),
            example="cmk_time_agent",
            required=True,
            validate=GRAPH_NAME_VALIDATOR,
        )


class TimeRange(BaseSchema):
    start = Timestamp(
        description="The approximate time of the first sample.",
        example=str(datetime.now() - timedelta(minutes=15)),
        required=True,
    )
    end = Timestamp(
        description="The approximate time of the last sample.",
        example=str(datetime.now()),
        required=True,
    )


class BaseRequestSchema(BaseSchema):
    time_range = Nested(
        TimeRange,
        description="The time range from which to source the metrics.",
        example={"start": str(datetime.now() - timedelta(minutes=15)), "end": str(datetime.now())},
        required=True,
    )

    reduce = String(
        enum=["min", "max", "average"],
        description=(
            "Specify how to reduce a segment of data points to a single data point of the output metric. "
            "This can be useful to find spikes in your data that would be smoothed out by computing the average."
        ),
        load_default="average",
        example="max",
    )


def reorganize_response(resp: dict[str, Any]) -> dict[str, Any]:
    """Reorganize a legacy WebApi response into the new format.

    >>> reorganize_response({
    ...    "step": 60,
    ...    "start_time": 123,
    ...    "end_time": 456,
    ...    "curves": [{
    ...        "color": "#ffffff",
    ...        "rrddata": [
    ...            1.0,
    ...            2.0,
    ...            3.0,
    ...            1.0,
    ...        ],
    ...        "line_type": "area",
    ...        "title": "RAM used"
    ...    }]
    ... })
    {'time_range': {'start': 123, 'end': 456}, 'step': 60, 'metrics': [{'color': '#ffffff', 'line_type': 'area', 'title': 'RAM used', 'data_points': [1.0, 2.0, 3.0, 1.0]}]}
    """
    curves = resp["curves"]
    for curve in curves:
        curve["data_points"] = curve["rrddata"]
        curve.pop("rrddata")

    return {
        "time_range": {
            "start": resp["start_time"],
            "end": resp["end_time"],
        },
        "step": resp["step"],
        "metrics": curves,
    }


def reorganize_time_range(time_range: dict[str, Any] | None) -> dict[str, Any] | None:
    """Reorganize a TimeRange into the legacy format the WebApi uses.

    >>> reorganize_time_range({'start': "1970-01-01T00:00:00Z", 'end': "1970-01-01T00:00:30Z"})
    {'time_range': ['1970-01-01T00:00:00Z', '1970-01-01T00:00:30Z']}
    """
    if time_range is None:
        return None
    return {"time_range": [time_range["start"], time_range["end"]]}


def graph_id_from_request(body: dict[str, Any]) -> str:
    """
    >>> graph_id_from_request({"type": "single_metric", "metric_id": "metric"})
    'METRIC_metric'
    >>> graph_id_from_request({"type": "predefined_graph", "graph_id": "graph"})
    'graph'
    """
    if body["type"] == "single_metric":
        return f"METRIC_{body['metric_id']}"
    return body["graph_id"]
