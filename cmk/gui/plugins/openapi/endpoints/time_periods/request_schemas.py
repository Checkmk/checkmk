#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.utils.dateutils import weekday_ids

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.watolib.groups import is_alias_used
from cmk.gui.watolib.timeperiods import TIMEPERIOD_ID_PATTERN, verify_timeperiod_name_exists

from cmk import fields


class TimePeriodName(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        "should_exist": "Name missing: {name!r}",
        "should_not_exist": "Name {name!r} already exists.",
    }

    def __init__(  # type: ignore[no-untyped-def]
        self,
        example,
        required=True,
        validate=None,
        should_exist: bool = True,
        **kwargs,
    ):
        self._should_exist = should_exist
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        _exists = verify_timeperiod_name_exists(value)
        if self._should_exist and not _exists:
            raise self.make_error("should_exist", name=value)
        if not self._should_exist and _exists:
            raise self.make_error("should_not_exist", name=value)


class TimePeriodAlias(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        "should_exist": "Time period alias does not exist: {name!r}",
        "should_not_exist": "Time period alias {name!r} already exists.",
        "should_not_be_builtin": "Time period alias {name!r} can't be a builtin",
    }

    def __init__(  # type: ignore[no-untyped-def]
        self,
        example,
        required=True,
        validate=None,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "should_exist_and_should_not_be_builtin",
        ] = "should_exist",
        **kwargs,
    ):
        self._presence = presence
        super().__init__(
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        # Empty String because validation works for non-timeperiod alias & time period name is
        # verified separately
        _is_new_alias, _ = is_alias_used("timeperiods", "", value)

        if self._presence == "should_exist" and _is_new_alias:
            raise self.make_error("should_exist", name=value)

        if self._presence == "should_not_exist" and not _is_new_alias:
            raise self.make_error("should_not_exist", name=value)

        if self._presence == "should_exist_and_should_not_be_builtin":
            if _is_new_alias:
                raise self.make_error("should_exist", name=value)
            if value == "Always":
                raise self.make_error("should_not_be_builtin", name=value)


class TimeRange(BaseSchema):
    start = fields.String(
        required=True,
        format="time",
        example="14:00:00",
        description="The start time of the period's time range",
    )
    end = fields.String(
        required=True,
        format="time",
        example="16:00:00",
        description="The end time of the period's time range",
    )


class TimeRangeActive(BaseSchema):
    day = fields.String(
        description="The day for which time ranges are to be specified. The 'all' "
        "option allows to specify time ranges for all days.",
        enum=["all"] + weekday_ids(),
        load_default="all",
    )
    time_ranges = fields.List(
        fields.Nested(TimeRange),
        example=[{"start": "13:00:00", "end": "19:00:00"}],
        load_default=[{"start": "00:00:00", "end": "23:59:00"}],
    )


class TimePeriodException(BaseSchema):
    date = fields.String(
        required=True,
        example="2020-01-01",
        format="date",
        description="The date of the time period exception." "8601 profile",
    )
    time_ranges = fields.List(
        fields.Nested(TimeRange),
        load_default=[],
        required=False,
        example=[{"start": "14:00", "end": "18:00"}],
    )


class CreateTimePeriod(BaseSchema):
    name = TimePeriodName(
        example="first",
        description="A unique name for the time period.",
        required=True,
        should_exist=False,
        pattern=TIMEPERIOD_ID_PATTERN,
    )
    alias = TimePeriodAlias(
        example="alias",
        description="An alias for the time period.",
        required=True,
        presence="should_not_exist",
    )
    active_time_ranges = fields.List(
        fields.Nested(TimeRangeActive),
        example=[{"day": "monday", "time_ranges": [{"start": "12:00:00", "end": "14:00:00"}]}],
        description="The list of active time ranges.",
        required=True,
    )
    exceptions = fields.List(
        fields.Nested(TimePeriodException),
        required=False,
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00:00", "end": "18:00:00"}]}],
        description="A list of additional time ranges to be added.",
    )
    exclude = fields.List(  # type: ignore[assignment]
        TimePeriodAlias(
            example="alias",
            description="The alias for a time period.",
            required=True,
            presence="should_exist_and_should_not_be_builtin",
        ),
        example=["alias"],
        description="A list of time period aliases whose periods are excluded.",
        required=False,
    )


class UpdateTimePeriod(BaseSchema):
    alias = TimePeriodAlias(
        example="new_alias",
        description="An alias for the time period",
        required=False,
        presence="should_not_exist",
    )
    active_time_ranges = fields.List(
        fields.Nested(TimeRangeActive),
        example=[
            {
                "day": "monday",
                "time_ranges": [{"start": "12:00:00", "end": "14:00:00"}],
            }
        ],
        description="The list of active time ranges which replaces the existing list of time ranges",
        required=False,
    )
    exceptions = fields.List(
        fields.Nested(TimePeriodException),
        required=False,
        example=[{"date": "2020-01-01", "time_ranges": [{"start": "14:00:00", "end": "18:00:00"}]}],
        description="A list of additional time ranges to be added.",
    )
