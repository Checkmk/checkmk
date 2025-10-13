#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime
from typing import NewType, NotRequired, TypedDict, TypeGuard

from dateutil.tz import tzlocal

from cmk.ccc.i18n import _
from cmk.utils.dateutils import Weekday, weekday_ids

__all__ = [
    "TimeperiodName",
    "TimeperiodSpec",
    "TimeperiodSpecs",
    "timeperiod_spec_alias",
]

TimeperiodName = NewType("TimeperiodName", str)
type DayTimeFrame = tuple[str, str]


# TODO: in python 3.13 we may be able to add support for the
# timeperiod exceptions - see https://peps.python.org/pep-0728/


class TimeperiodSpec(TypedDict):
    # In addition to the defined fields the data structures allows arbitrary
    # fields in the following format (standing for exceptions). This is not
    # supported by typed dicts, so we definitely should use something else
    # during runtime. %Y-%m-%d: list[tuple[str, str]]
    alias: str
    monday: NotRequired[list[DayTimeFrame]]
    tuesday: NotRequired[list[DayTimeFrame]]
    wednesday: NotRequired[list[DayTimeFrame]]
    thursday: NotRequired[list[DayTimeFrame]]
    friday: NotRequired[list[DayTimeFrame]]
    saturday: NotRequired[list[DayTimeFrame]]
    sunday: NotRequired[list[DayTimeFrame]]
    exclude: NotRequired[list[TimeperiodName]]


TimeperiodSpecs = Mapping[TimeperiodName, TimeperiodSpec]


def get_all_timeperiods(raw_configured_timeperiods: object) -> TimeperiodSpecs:
    return {
        **_parse_configured_timeperiods(raw_configured_timeperiods),
        **builtin_timeperiods(),
    }


def _parse_configured_timeperiods(raw: object) -> TimeperiodSpecs:
    if not isinstance(raw, Mapping):
        raise TypeError(f"Error parsing configured timeperiods: {raw!r}")

    # This is easier once all keys are mandatory...
    return {
        TimeperiodName(raw_name): TimeperiodSpec(
            alias=str(raw_spec["alias"]),
            **{  # type: ignore[typeddict-item]
                k: [_parse_daytimeframe(t) for t in v]
                for k, v in raw_spec.items()
                if k not in ("alias", "exclude")
            },
            **(
                {"exclude": [TimeperiodName(e) for e in raw_spec["exclude"]]}
                if "exclude" in raw_spec
                else {}
            ),
        )
        for raw_name, raw_spec in raw.items()
    }


def _parse_daytimeframe(value: object) -> DayTimeFrame:
    match value:
        case (start, end):
            return (str(start), str(end))
    raise TypeError(f"Error parsing DayTimeFrame: {value!r}")


def remove_builtin_timeperiods(timeperiods: TimeperiodSpecs) -> TimeperiodSpecs:
    return {k: timeperiods[k] for k in timeperiods.keys() - builtin_timeperiods().keys()}


def is_builtin_timeperiod(name: TimeperiodName) -> bool:
    return name in builtin_timeperiods()


def builtin_timeperiods() -> TimeperiodSpecs:
    return {
        TimeperiodName("24X7"): TimeperiodSpec(
            alias=_("Always"),
            monday=[("00:00", "24:00")],
            tuesday=[("00:00", "24:00")],
            wednesday=[("00:00", "24:00")],
            thursday=[("00:00", "24:00")],
            friday=[("00:00", "24:00")],
            saturday=[("00:00", "24:00")],
            sunday=[("00:00", "24:00")],
        )
    }


def _is_time_range(obj: object) -> TypeGuard[DayTimeFrame]:
    return isinstance(obj, tuple) and len(obj) == 2 and all(isinstance(item, str) for item in obj)


def is_time_range_list(obj: object) -> TypeGuard[list[tuple[str, str]]]:
    return isinstance(obj, list) and all(_is_time_range(item) for item in obj)


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = "") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception(f"invalid timeperiod alias {alias!r}")


type _Logger = Callable[[str], object]


class TimeperiodActiveCoreLookup(Mapping[str, bool]):
    """A mapping that queries livestatus for timeperiod states on first access.

    The response of the livestatus query is cached for the lifetime of this object.
    """

    def __init__(
        self,
        livestatus_access: Callable[[_Logger], Mapping[str, bool] | None],
        log: _Logger,
    ) -> None:
        self._livestatus_access = livestatus_access
        self._log = log
        self.__core_response: Mapping[str, bool] | None = None

    @property
    def _core_response(self) -> Mapping[str, bool]:
        if self.__core_response is not None:
            return self.__core_response

        if (response := self._livestatus_access(self._log)) is None:
            return {}

        self.__core_response = response
        return self.__core_response

    def __getitem__(self, key: str) -> bool:
        return self._core_response.__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._core_response)

    def __len__(self) -> int:
        return len(self._core_response)


def _is_time_in_timeperiod(
    current_datetime: datetime,
    time_tuple_list: Sequence[tuple[str, str]],
    day: datetime | None = None,
) -> bool:
    current_time = current_datetime.strftime("%H:%M")
    if day and day.date() != current_datetime.date():
        return False
    for start, end in time_tuple_list:
        if start <= current_time <= end:
            return True
    return False


def is_timeperiod_active(
    timestamp: float,
    timeperiod_name: TimeperiodName,
    all_timeperiods: TimeperiodSpecs,
) -> bool:
    if (timeperiod_definition := all_timeperiods.get(timeperiod_name)) is None:
        raise ValueError(f"Time period {timeperiod_name} not found.")

    if _is_timeperiod_excluded_via_timeperiod(
        timestamp=timestamp,
        timeperiod_definition=timeperiod_definition,
        all_timeperiods=all_timeperiods,
    ):
        return False

    days = weekday_ids()
    current_datetime = datetime.fromtimestamp(timestamp, tzlocal())
    if _is_timeperiod_active_via_exception(
        timeperiod_definition,
        days,
        current_datetime,
    ):
        return True

    if (weekday := days[current_datetime.weekday()]) in timeperiod_definition:
        time_ranges = timeperiod_definition[weekday]
        assert is_time_range_list(time_ranges)
        return _is_time_in_timeperiod(current_datetime, time_ranges)

    return False


def _is_timeperiod_excluded_via_timeperiod(
    timestamp: float,
    timeperiod_definition: TimeperiodSpec,
    all_timeperiods: TimeperiodSpecs,
) -> bool:
    for excluded_timeperiod in timeperiod_definition.get("exclude", []):
        assert isinstance(excluded_timeperiod, str)
        return is_timeperiod_active(
            timestamp=timestamp,
            timeperiod_name=excluded_timeperiod,
            all_timeperiods=all_timeperiods,
        )

    return False


def _is_timeperiod_active_via_exception(
    timeperiod_definition: TimeperiodSpec,
    days: Sequence[Weekday],
    current_time: datetime,
) -> bool:
    for key, value in timeperiod_definition.items():
        if key in [*days, "alias", "exclude"]:
            continue

        try:
            day = datetime.strptime(key, "%Y-%m-%d")
        except ValueError:
            continue

        if not is_time_range_list(value):
            continue

        return _is_time_in_timeperiod(current_time, value, day)

    return False


def validate_timeperiod_exceptions(timeperiod: TimeperiodSpec) -> None:
    """Validate the time period exceptions.

    Note: in the timeperiod dict the exceptions are stored as additional fields besides
    the fields defined in TimeperiodSpec. This is obviously not ideal and should be changed

    """
    for name, value in timeperiod.items():
        if name in TimeperiodSpec.__annotations__:  # see docstring
            continue

        try:
            datetime.strptime(name, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid time period field: {name}")

        assert is_time_range_list(value)
        for time_range in value:
            _validate_time_range(time_range)


def validate_day_time_ranges(timeperiod: TimeperiodSpec) -> None:
    day_names = weekday_ids()
    for name in day_names:
        if name not in timeperiod:
            continue

        for time_range in timeperiod[name]:
            _validate_time_range(time_range)


def _validate_time_range(time_range: DayTimeFrame) -> None:
    _validate_time(time_range[0])
    _validate_time(time_range[1])

    start_hour, start_minute = map(int, time_range[0].split(":"))
    end_hour, end_minute = map(int, time_range[1].split(":"))

    if (end_hour * 60 + end_minute) < (start_hour * 60 + start_minute):
        raise ValueError(f"Invalid time range: {time_range}")


def _validate_time(value: str) -> None:
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
