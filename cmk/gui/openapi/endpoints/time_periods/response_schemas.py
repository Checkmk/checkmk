#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObjectCollection, Linkable
from cmk.utils.dateutils import weekday_ids

TIME_FIELD = fields.String(
    example="14:00",
    format="time",
    description="The hour of the time period.",
)


class ConcreteTimeRange(BaseSchema):
    start = TIME_FIELD
    end = TIME_FIELD


class ConcreteTimeRangeActive(BaseSchema):
    day = fields.String(
        description="The day for which the time ranges are specified",
        enum=weekday_ids(),
    )
    time_ranges = fields.List(
        fields.Nested(ConcreteTimeRange),
    )


class ConcreteTimePeriodException(BaseSchema):
    date = fields.String(
        example="2020-01-01",
        format="date",
        description="The date of the time period exception.8601 profile",
    )
    time_ranges = fields.List(
        fields.Nested(ConcreteTimeRange),
        example="[{'start': '14:00', 'end': '18:00'}]",
    )


class TimePeriodAttrsResponse(BaseSchema):
    alias = fields.String(
        description="The alias of the time period",
        example="alias",
    )
    active_time_ranges = fields.List(
        fields.Nested(ConcreteTimeRangeActive),
        description="The days for which time ranges were specified",
        example={"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]},
    )
    exceptions = fields.List(
        fields.Nested(ConcreteTimePeriodException),
        description="Specific day exclusions with their list of time ranges",
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}],
    )
    exclude = fields.List(  # type: ignore[assignment]
        fields.String(
            description="Name of excluding time period",
        ),
        description="The collection of time period names whose periods are excluded",
        example=["time_period_1", "time_period_2", "time_period_3"],
    )


EXAMPLE_TIME_PERIOD = {
    "alias": "holidays",
    "active_time_ranges": [
        {
            "day": "monday",
            "time_ranges": [{"start": "12:00", "end": "15:00"}],
        },
    ],
    "exceptions": [
        {
            "date": "2023-01-01",
            "time_ranges": [{"start": "12:30", "end": "13:30"}],
        },
    ],
    "exclude": [
        "time_period_1",
        "time_period_2",
        "time_period_3",
    ],
}


class TimePeriodResponse(Linkable):
    domainType = fields.Constant(
        "time_period",
        description="The domain type of the object.",
    )
    id = fields.String(
        description="The unique identifier for this time period.", example="time_period_name"
    )
    title = fields.String(
        description="The time period name.",
        example="time_period_alias.",
    )
    members: gui_fields.Field = fields.Dict(
        description="The container for external resources, like linked foreign objects or actions.",
    )
    extensions = fields.Nested(
        TimePeriodAttrsResponse,
        description="The time period attributes.",
        example=EXAMPLE_TIME_PERIOD,
    )


class TimePeriodResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "time_period",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(TimePeriodResponse),
        description="A list of time period objects.",
        example=[
            {
                "links": [],
                "domainType": "time_period",
                "id": "time_period",
                "members": {},
                "extensions": EXAMPLE_TIME_PERIOD,
            }
        ],
    )
