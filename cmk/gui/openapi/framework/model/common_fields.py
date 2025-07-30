#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
import ipaddress
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Annotated, ClassVar, Literal, overload, override, Self

from annotated_types import Ge
from pydantic import (
    Discriminator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    model_validator,
    PlainSerializer,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema, CoreSchema

from cmk.gui.config import active_config
from cmk.gui.fields.fields_filter import FieldsFilter, parse_fields_filter
from cmk.gui.openapi.framework import QueryParam
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.framework.model.omitted import ApiOmitted
from cmk.gui.valuespec import TimerangeValue
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree


def _validate_regex(value: str) -> str:
    """Check if the value is a valid regex."""
    re.compile(value)
    return value


class RegexString(str):
    """Normal string that is validated as a regex."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: CoreSchema, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            _validate_regex, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema.setdefault("format", "regex")
        return json_schema


def _validate_ipv4(value: str) -> str:
    """Check if the value is a valid IPv4 address."""
    ipaddress.IPv4Address(value)
    return value


class IPv4String(str):
    """Normal string that is validated as an IPv4 address."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: CoreSchema, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            _validate_ipv4, core_schema.str_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema.setdefault("format", "ipv4")
        return json_schema


FieldsFilterType = Annotated[
    Annotated[FieldsFilter, TypedPlainValidator(str, parse_fields_filter)] | ApiOmitted,
    QueryParam(
        description="""The fields to include/exclude.

The syntax is a comma-separated list of field paths.
Each field path is a sequence of field names separated by a tilde (`~`).
Field names may contain alphanumeric characters, dashes (`-`) and underscores (`_`).
The field path may be followed by a list of subfields enclosed in parentheses (`(` and `)`).

The outermost fields must be enclosed in parentheses and may be prefixed with an exclamation mark (`!`) to negate the selection.

Examples:
- `(ipaddress)` selects the field `ipaddress`, all other fields will be omitted.
- `!(ipaddress)` excludes the field `ipaddress`, all other fields will be included.
- `(ipaddress,ipv6address)` selects only the fields `ipaddress` and `ipv6address`.
- `(attributes~ipaddress)` selects the field `ipaddress` within `attributes`, all other fields (not just within attributes) will be omitted.
- `(attributes(ipaddress,ipv6address))` selects the fields `ipaddress` and `ipv6address` within `attributes`, again all other fields will be omitted.
- `!(extensions~attributes(ipaddress,ipv6address))` excludes the fields `ipaddress` and `ipv6address` within `attributes` under `extensions`, all other fields will be included.
""",
        example="(id)",
    ),
]


class _FolderValidation:
    @staticmethod
    def _normalize_folder(folder_id: str) -> str:
        r"""Normalizes a folder representation.

        This means replacing the separators with slashes, and stripping extra ones.
        The leading separator will also be removed!

        Examples:

            >>> _FolderValidation._normalize_folder("\\")
            ''

            >>> _FolderValidation._normalize_folder("~")
            ''

            >>> _FolderValidation._normalize_folder("/foo/bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("\\foo\\bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("~foo~bar")
            'foo/bar'

            >>> _FolderValidation._normalize_folder("/foo/bar/")
            'foo/bar'
        """
        for sep in ("\\", "~"):
            folder_id = folder_id.replace(sep, "/")

        return folder_id.strip("/")

    @staticmethod
    def _is_hex(hex_string: str) -> bool:
        try:
            int(hex_string, 16)
            return True
        except ValueError:
            return False

    @classmethod
    def validate(cls, value: str) -> Folder:
        tree = folder_tree()
        value = cls._normalize_folder(value)
        if value == "":
            return tree.root_folder()

        if cls._is_hex(value):
            return tree._by_id(value)

        return tree.folder(value)

    @staticmethod
    def serialize(value: Folder) -> str:
        return "/" + value.path()


AnnotatedFolder = Annotated[
    Folder,
    TypedPlainValidator(str, _FolderValidation.validate),
    PlainSerializer(_FolderValidation.serialize, return_type=str),
]

type _PositiveInt = Annotated[int, Ge(0)]


@api_model
class _BaseTimerangeValue(ABC):
    @abstractmethod
    def to_internal(self) -> TimerangeValue:
        """Convert the timerange value to an internal representation."""
        raise NotImplementedError()


@api_model
class _TimerangeGraph(_BaseTimerangeValue):
    timerange_type: Literal["graph"] = api_field(
        serialization_alias="type", description="Select a predefined graph timerange."
    )
    duration: Annotated[int, Ge(1)] = api_field(description="The duration in seconds.")

    def __post_init__(self) -> None:
        for timerange in active_config.graph_timeranges:
            if timerange["duration"] == self.duration:
                return

        raise ValueError("The selected graph timerange does not exist.")

    def to_internal(self) -> TimerangeValue:
        return self.duration


@api_model
class _TimerangeAge(_BaseTimerangeValue):
    timerange_type: Literal["age"] = api_field(
        serialization_alias="type", description="Manually define a relative timerange."
    )
    days: _PositiveInt | ApiOmitted = api_field(
        description="The number of days to look back.",
        default_factory=ApiOmitted,
    )
    hours: _PositiveInt | ApiOmitted = api_field(
        description="The number of hours to look back.",
        default_factory=ApiOmitted,
    )
    minutes: _PositiveInt | ApiOmitted = api_field(
        description="The number of minutes to look back.",
        default_factory=ApiOmitted,
    )
    seconds: _PositiveInt | ApiOmitted = api_field(
        description="The number of seconds to look back.",
        default_factory=ApiOmitted,
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not any(
            (
                self.days,
                self.hours,
                self.minutes,
                self.seconds,
            )
        ):
            raise ValueError("At least one of days, hours, minutes or seconds must be set.")
        return self

    @override
    def to_internal(self) -> TimerangeValue:
        age = self.seconds or 0
        age += (self.minutes or 0) * 60
        age += (self.hours or 0) * 3600
        age += (self.days or 0) * 86400
        return "age", age


@api_model
class _TimerangeDate(_BaseTimerangeValue):
    timerange_type: Literal["date"] = api_field(
        serialization_alias="type", description="Manually define a fixed timerange."
    )
    start: dt.date = api_field(
        description="The start date in ISO format (YYYY-MM-DD).",
    )
    end: dt.date = api_field(
        description="The end date in ISO format (YYYY-MM-DD).",
    )

    @staticmethod
    def _date_to_timestamp(value: dt.date) -> float:
        """Convert a date to a UTC timestamp."""
        return dt.datetime(
            year=value.year, month=value.month, day=value.day, tzinfo=dt.UTC
        ).timestamp()

    @override
    def to_internal(self) -> TimerangeValue:
        return "date", (self._date_to_timestamp(self.start), self._date_to_timestamp(self.end))


@api_model
class _TimerangeDateTime(_BaseTimerangeValue):
    timerange_type: Literal["time"] = api_field(
        serialization_alias="type", description="Manually define a fixed timerange with UTC times."
    )
    start: dt.datetime = api_field(
        description="The start date and time in ISO format (YYYY-MM-DDTHH:MM:SS).",
    )
    end: dt.datetime = api_field(
        description="The end date and time in ISO format (YYYY-MM-DDTHH:MM:SS).",
    )

    @override
    def to_internal(self) -> TimerangeValue:
        return "date", (self.start.timestamp(), self.end.timestamp())


@api_model
class _TimerangePredefined(_BaseTimerangeValue):
    # NOTE: these are more user-friendly names for the timeranges defined in the Timerange ValueSpec
    type _Predefined = Literal[
        "last_4_hours",
        "last_25_hours",
        "last_8_days",
        "last_35_days",
        "last_400_days",
        "today",
        "yesterday",
        "7_days_ago",
        "8_days_ago",
        "this_week",
        "last_week",
        "2_weeks_ago",
        "this_month",
        "last_month",
        "this_year",
        "last_year",
    ]
    MAPPING: ClassVar[Mapping[_Predefined, TimerangeValue]] = {
        "last_4_hours": "4h",
        "last_25_hours": "25h",
        "last_8_days": "8d",
        "last_35_days": "35d",
        "last_400_days": "400d",
        "today": "d0",
        "yesterday": "d1",
        "7_days_ago": "d7",
        "8_days_ago": "d8",
        "this_week": "w0",
        "last_week": "w1",
        "2_weeks_ago": "w2",
        "this_month": "m0",
        "last_month": "m1",
        "this_year": "y0",
        "last_year": "y1",
    }
    timerange_type: Literal["predefined"] = api_field(
        serialization_alias="type", description="Select a predefined timerange."
    )
    value: _Predefined = api_field(description="The timerange.")

    @override
    def to_internal(self) -> TimerangeValue:
        return self.MAPPING[self.value]


type TimerangeModel = Annotated[
    _TimerangePredefined | _TimerangeGraph | _TimerangeAge | _TimerangeDate,
    Discriminator("timerange_type"),
]
type TimerangeWithTimesModel = Annotated[
    _TimerangePredefined | _TimerangeGraph | _TimerangeAge | _TimerangeDate | _TimerangeDateTime,
    Discriminator("timerange_type"),
]


@overload
def timerange_from_internal(
    timerange: TimerangeValue, with_times: Literal[False] = False
) -> TimerangeModel: ...


@overload
def timerange_from_internal(
    timerange: TimerangeValue, with_times: Literal[True]
) -> TimerangeWithTimesModel: ...


def timerange_from_internal(
    timerange: TimerangeValue, with_times: bool = False
) -> TimerangeModel | TimerangeWithTimesModel:
    """Convert an internal timerange value to the API model."""
    match timerange:
        case str() as lookup:
            for key, value in _TimerangePredefined.MAPPING.items():
                if lookup == value:
                    return _TimerangePredefined(timerange_type="predefined", value=key)
        case int() as duration:
            return _TimerangeGraph(timerange_type="graph", duration=duration)
        # mypy doesn't understand that this can only be an int
        case ("age", age) if isinstance(age, int):
            return _TimerangeAge(
                timerange_type="age",
                days=age // 86400,
                hours=(age % 86400) // 3600,
                minutes=(age % 3600) // 60,
                seconds=age % 60,
            )
        case ("date", (start, end)):
            return _TimerangeDate(
                timerange_type="date",
                start=dt.date.fromtimestamp(start),
                end=dt.date.fromtimestamp(end),
            )
        case ("time", (start, end)) if with_times:
            return _TimerangeDateTime(
                timerange_type="time",
                start=dt.datetime.fromtimestamp(start, dt.UTC),
                end=dt.datetime.fromtimestamp(end, dt.UTC),
            )
    raise ValueError(f"Invalid timerange value: {timerange}")
