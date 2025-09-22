#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from collections.abc import Callable, Sequence
from enum import auto, Enum
from typing import Any, assert_never

import dateutil.parser

from cmk.gui.form_specs.unstable import DatePicker, TimePicker
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec


class DateTimeFormat(Enum):
    DATE = auto()  # saved as int (unix timestamp)
    DATETIME = auto()  # saved as int (unix timestamp)
    TIME = auto()  # saved as tuple[int, int] (hour, minute)


def AbsoluteTimestamp(
    title: Title,
    use_format: DateTimeFormat,
    custom_validate: Sequence[Callable[[tuple[object, ...]], None]] | None = None,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    def from_disk(value: object) -> list[str]:
        match use_format:
            case DateTimeFormat.DATE:
                if not isinstance(value, int):
                    raise TypeError("Expected int for DATE format")
                dt = datetime.datetime.fromtimestamp(value)
                return [f"{dt.year:02}-{dt.month:02}-{dt.day:02}"]
            case DateTimeFormat.DATETIME:
                if not isinstance(value, int):
                    raise TypeError("Expected int for DATETIME format")
                dt = datetime.datetime.fromtimestamp(value)
                return [f"{dt.year}-{dt.month:02}-{dt.day:02}", f"{dt.hour:02}:{dt.minute:02}"]
            case DateTimeFormat.TIME:
                if not isinstance(value, list):
                    raise TypeError("Expected list[int] for TIME format")
                return [f"{value[0]}:{value[1]}"]
            case other:
                assert_never(other)

    def to_disk(value: object) -> int | list[int]:
        if not isinstance(value, tuple):
            raise TypeError("Unable to serialize invalid timestamp format: {type(value)}")
        match use_format:
            case DateTimeFormat.TIME:
                hour, minute = map(int, value[0].split(":"))
                return [hour, minute]
            case _:
                parsed_time = dateutil.parser.isoparse("T".join(value))
                return int(parsed_time.timestamp())

    elements: list[FormSpec[Any]] = []
    if use_format in (DateTimeFormat.DATE, DateTimeFormat.DATETIME):
        elements.extend([DatePicker(title=Title("Date"))])

    if use_format in (DateTimeFormat.TIME, DateTimeFormat.DATETIME):
        elements.extend([TimePicker(title=Title("Time"))])

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=Tuple(
            title=title,
            layout="horizontal_titles_top",
            elements=elements,
            custom_validate=custom_validate,
        ),
        from_disk=from_disk,
        to_disk=to_disk,
    )
