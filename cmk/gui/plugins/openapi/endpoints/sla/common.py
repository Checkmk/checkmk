#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.base import BaseSchema

from cmk import fields


class TimeRangeBase(BaseSchema):
    range_type = fields.String(
        required=True,
        description="The type of the time range.",
        enum=["pre_defined", "custom"],
        example="pre_defined",
    )


class PreDefinedTimeRange(TimeRangeBase):
    range = fields.String(
        enum=[
            "today",
            "yesterday",
            "this_week",
            "last_week",
            "this_month",
            "last_month",
            "this_year",
            "last_year",
        ],
        description="The pre-defined time range.",
        example="today",
    )


class CustomTimeRange(TimeRangeBase):
    start = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The start datetime of the SLA compute period range. The format has to conform "
        "to the ISO 8601 profile",
    )
    end = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the SLA compute period range. The format has to conform "
        "to the ISO 8601 profile",
        format="iso8601",
    )
