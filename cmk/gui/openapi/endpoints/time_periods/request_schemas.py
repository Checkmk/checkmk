#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Collection
from typing import Any, Literal

import marshmallow
from marshmallow.utils import from_iso_time

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
        "should_not_be_builtin": "Time period alias {name!r} can't be a built-in",
    }

    def __init__(
        self,
        example: str,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "should_exist_and_should_not_be_builtin",
        ] = "should_exist",
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        should_exist: bool = True,
        **kwargs: Any,
    ):
        self._should_exist = should_exist
        self._presence = presence
        super().__init__(
            example=example,
            pattern=TIMEPERIOD_ID_PATTERN,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        _exists = verify_timeperiod_name_exists(value)

        if self._presence == "should_exist" and not _exists:
            raise self.make_error("should_exist", name=value)

        if self._presence == "should_not_exist" and _exists:
            raise self.make_error("should_not_exist", name=value)

        if self._presence == "should_exist_and_should_not_be_builtin":
            if not _exists:
                raise self.make_error("should_exist", name=value)
            if value == "24X7":
                raise self.make_error("should_not_be_builtin", name=value)


class TimePeriodAlias(fields.String):
    """A field representing a time_period name"""

    default_error_messages = {
        "should_exist": "Time period alias does not exist: {name!r}",
        "should_not_exist": "Time period alias {name!r} already exists.",
        "should_not_be_builtin": "Time period alias {name!r} can't be a built-in",
    }

    def __init__(
        self,
        example: str,
        required: bool = True,
        validate: Callable[[object], bool] | Collection[Callable[[object], bool]] | None = None,
        presence: Literal[
            "should_exist",
            "should_not_exist",
            "should_exist_and_should_not_be_builtin",
        ] = "should_exist",
        **kwargs: Any,
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

    @marshmallow.validates_schema
    def validate_start_before_end(self, data, **_kwargs):
        self._validate_times(data)
        self._validate_time_order(data)

    @staticmethod
    def _validate_time_order(data: Any) -> None:
        def _day_timestamp(time_string: str) -> int:
            """
            Examples:
                >>> _day_timestamp("13:00")
                780
                >>> _day_timestamp("00:00")
                0
                >>> _day_timestamp("24:00")
                1440
            """
            # we also care about 24:00 but Python datetime doesn't
            time_components = time_string.split(":")
            return int(time_components[0]) * 60 + int(time_components[1])

        if _day_timestamp(data["start"]) > _day_timestamp(data["end"]):
            raise marshmallow.ValidationError(
                f"Start time ({data['start']}) must be before end time ({data['end']})."
            )

    @staticmethod
    def _validate_times(data: Any) -> None:
        for time_reference in ("start", "end"):
            time_string = data[time_reference]
            time_components = time_string.split(":")
            if time_components[0] == "24":
                if time_components[1] == "00":
                    return

                raise marshmallow.ValidationError(f"Invalid {time_reference} time: {time_string}")

            try:
                from_iso_time(time_string)
            except ValueError:
                raise marshmallow.ValidationError(f"Invalid {time_reference} time: {time_string}")


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
        description="The date of the time period exception.8601 profile",
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
        presence="should_not_exist",
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
        TimePeriodName(
            example="time_name",
            description="A unique name for the time period.",
            required=True,
            presence="should_exist",
        ),
        example=["name"],
        description="A list of time period names whose periods are excluded.",
        required=False,
    )


class UpdateTimePeriod(BaseSchema):
    alias = fields.String(
        example="new_alias",
        description="An alias for the time period",
        required=False,
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

    exclude = fields.List(  # type: ignore[assignment]
        TimePeriodName(
            example="time_name",
            description="A unique name for the time period.",
            required=True,
            presence="should_exist_and_should_not_be_builtin",
        ),
        example=["time_name"],
        description="A list of time period names whose periods are excluded.",
        required=False,
    )
