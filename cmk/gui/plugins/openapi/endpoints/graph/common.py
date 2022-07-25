#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from datetime import datetime, timedelta
from typing import Any, Optional

import marshmallow

from cmk.gui.fields import Timestamp
from cmk.gui.fields.base import BaseSchema

from cmk.fields import Nested, String

GRAPH_NAME_REGEX = r"^\w[_\-\w\d]*$"
GRAPH_NAME_ERROR_MESSAGE = "{input} is not a valid value for this field. It must match the pattern {regex} and contain onlz ASCII characters."
GRAPH_NAME_VALIDATOR = marshmallow.validate.Regexp(
    regex=GRAPH_NAME_REGEX, error=GRAPH_NAME_ERROR_MESSAGE, flags=re.ASCII
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
        description="The time range from which to source the graph.",
        example={"start": str(datetime.now() - timedelta(minutes=15)), "end": str(datetime.now())},
        required=True,
    )
    consolidation_function = String(
        enum=["min", "max", "average"],
        description="Data points get summarized over time by taking the minimum, maximum and average values over a specific time range. This field governs which value type is returned when data from this time range is requested.",
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
    {'time_range': {'start': 123, 'end': 456}, 'step': 60, 'curves': [{'color': '#ffffff', 'line_type': 'area', 'title': 'RAM used', 'rrd_data': [1.0, 2.0, 3.0, 1.0]}]}
    """
    curves = resp["curves"]
    for curve in curves:
        curve["rrd_data"] = curve["rrddata"]
        curve.pop("rrddata")

    return {
        "time_range": {
            "start": resp["start_time"],
            "end": resp["end_time"],
        },
        "step": resp["step"],
        "curves": curves,
    }


def reorganize_time_range(time_range: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Reorganize a TimeRange into the legacy format the WebApi uses.

    >>> reorganize_time_range({'start': "1970-01-01T00:00:00Z", 'end': "1970-01-01T00:00:30Z"})
    {'time_range': ['1970-01-01T00:00:00Z', '1970-01-01T00:00:30Z']}
    """
    if time_range is None:
        return None
    return {"time_range": [time_range["start"], time_range["end"]]}
