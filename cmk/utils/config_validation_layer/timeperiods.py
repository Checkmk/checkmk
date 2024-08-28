#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator, ValidationError

from cmk.ccc.i18n import _

from cmk.utils.dateutils import weekday_ids

from cmk.gui.exceptions import MKConfigError  # pylint: disable=cmk-module-layer-violation

ALIASES = list[str]
TIME_RANGE = tuple[str, str]
EXCEPTIONS = dict[str, list[TIME_RANGE]]


def validate_time(value: str) -> None:
    time_components = value.split(":")
    if len(time_components) != 2:
        raise ValueError(f"Invalid time: {value}")

    if time_components[0] == "24" and time_components[1] == "00":
        return

    try:
        hour = int(time_components[0])
        minute = int(time_components[1])

    except ValueError:
        raise ValueError(f"Invalid time: {value}")

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time: {value}")


def validate_time_range(time_range: TIME_RANGE) -> None:
    validate_time(time_range[0])
    validate_time(time_range[1])

    start_hour, start_minute = map(int, time_range[0].split(":"))
    end_hour, end_minute = map(int, time_range[1].split(":"))

    if (end_hour * 60 + end_minute) < (start_hour * 60 + start_minute):
        raise ValueError(f"Invalid time range: {time_range}")


class TimePeriod(BaseModel):
    model_config = {
        "frozen": True,
        "json_schema_extra": {"exclude": ["name"]},
    }

    name: str
    alias: str
    exclude: ALIASES | None = None
    exception: EXCEPTIONS | None = None
    monday: list[TIME_RANGE] | None = None
    tuesday: list[TIME_RANGE] | None = None
    wednesday: list[TIME_RANGE] | None = None
    thursday: list[TIME_RANGE] | None = None
    friday: list[TIME_RANGE] | None = None
    saturday: list[TIME_RANGE] | None = None
    sunday: list[TIME_RANGE] | None = None

    @field_validator("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    @classmethod
    def validate_time_range(cls, value: list[TIME_RANGE]) -> list[TIME_RANGE]:
        for time_range in value:
            validate_time_range(time_range)
        return value

    @model_validator(mode="before")
    @classmethod
    def check_extra_fields(cls, values: dict) -> dict:
        pre_processed_data = {}
        day_names = weekday_ids()
        model_has_day_fields = False
        for name, value in values.items():
            if name in cls.model_fields:
                model_has_day_fields = model_has_day_fields or (name in day_names)
                pre_processed_data[name] = value

            else:
                # Only ISO dates allowed as extra fields names, and their values must be List[TIME_RANGE]
                datetime.strptime(name, "%Y-%m-%d")
                if not isinstance(value, list):
                    raise ValueError(f"Invalid time range: {value}")
                for time_range in value:
                    validate_time_range(time_range)

                if "exception" not in pre_processed_data:
                    pre_processed_data["exception"] = {}
                pre_processed_data["exception"][name] = value

        if not model_has_day_fields:
            raise ValueError("Missing time periods")

        return pre_processed_data


def validate_timeperiods(timeperiods: dict[str, Any]) -> None:
    for name, timeperiod in timeperiods.items():
        validate_timeperiod(name, timeperiod)


def validate_timeperiod(name: str, timeperiod: dict) -> None:
    try:
        TimePeriod(name=name, **timeperiod)
    except ValidationError as exc:
        raise MKConfigError(_("Error: passwords.mk validation %s") % exc.errors())
