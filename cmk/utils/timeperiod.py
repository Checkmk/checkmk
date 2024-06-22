#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import datetime
from typing import TypeAlias, TypeGuard

from dateutil.tz import tzlocal

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
from cmk.utils.caching import cache_manager
from cmk.utils.dateutils import Weekday
from cmk.utils.exceptions import MKTimeout
from cmk.utils.i18n import _

__all__ = [
    "TimeperiodName",
    "TimeperiodSpec",
    "TimeperiodSpecs",
    "timeperiod_spec_alias",
]

TimeperiodName: TypeAlias = str

# TODO: TimeperiodSpec should really be a class or at least a NamedTuple! We
# can easily transform back and forth for serialization.
TimeperiodSpec = dict[str, str | list[str] | list[tuple[str, str]]]
# class TimeperiodSpec(TypedDict):
#    alias: str
#    monday: NotRequired[list[tuple[str, str]]]
#    tuesday: NotRequired[list[tuple[str, str]]]
#    wednesday: NotRequired[list[tuple[str, str]]]
#    thursday: NotRequired[list[tuple[str, str]]]
#    friday: NotRequired[list[tuple[str, str]]]
#    saturday: NotRequired[list[tuple[str, str]]]
#    sunday: NotRequired[list[tuple[str, str]]]
#    exclude: NotRequired[list[TimeperiodName]]
#    # In addition to the above fields the data structures allows arbitrary
#    # fields in the following format. This is not supported by typed dicts,
#    # so we definetely should use something else during runtime.
#    # %Y-%m-%d: list[tuple[str, str]]

TimeperiodSpecs = dict[TimeperiodName, TimeperiodSpec]


def is_time_range_list(obj: object) -> TypeGuard[list[tuple[str, str]]]:
    return isinstance(obj, list) and all(
        isinstance(item, tuple)
        and len(item) == 2
        and all(isinstance(subitem, str) for subitem in item)
        for item in obj
    )


# TODO: We should really parse our configuration file and use a
# class/NamedTuple, see above.
def timeperiod_spec_alias(timeperiod_spec: TimeperiodSpec, default: str = "") -> str:
    alias = timeperiod_spec.get("alias", default)
    if isinstance(alias, str):
        return alias
    raise Exception(f"invalid timeperiod alias {alias!r}")


def check_timeperiod(timeperiod: TimeperiodName) -> bool:
    """Check if a time period is currently active. We have no other way than
    doing a Livestatus query. This is not really nice, but if you have a better
    idea, please tell me..."""
    # Let exceptions happen, they will be handled upstream.
    try:
        update_timeperiods_cache()
    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise

        # If the query is not successful better skip this check then fail
        return True

    # Note: This also returns True when the time period is unknown
    #       The following function time period_active handles this differently
    return cache_manager.obtain_cache("timeperiods_cache").get(timeperiod, True)


def timeperiod_active(timeperiod: TimeperiodName) -> bool | None:
    """Returns
    True : active
    False: inactive
    None : unknown timeperiod

    Raises an exception if e.g. a timeout or connection error appears.
    This way errors can be handled upstream."""
    update_timeperiods_cache()
    return cache_manager.obtain_cache("timeperiods_cache").get(timeperiod)


def update_timeperiods_cache() -> None:
    # { "last_update": 1498820128, "timeperiods": [{"24x7": True}] }
    # The value is store within the config cache since we need a fresh start on reload
    tp_cache = cache_manager.obtain_cache("timeperiods_cache")

    if not tp_cache:
        connection = livestatus.LocalConnection()
        connection.set_timeout(2)
        response = connection.query("GET timeperiods\nColumns: name in")
        for tp_name, tp_active in response:
            tp_cache[tp_name] = bool(tp_active)


def cleanup_timeperiod_caches() -> None:
    cache_manager.obtain_cache("timeperiods_cache").clear()


cmk.utils.cleanup.register_cleanup(cleanup_timeperiod_caches)


def builtin_timeperiods() -> TimeperiodSpecs:
    return {
        "24X7": {
            "alias": _("Always"),
            "monday": [("00:00", "24:00")],
            "tuesday": [("00:00", "24:00")],
            "wednesday": [("00:00", "24:00")],
            "thursday": [("00:00", "24:00")],
            "friday": [("00:00", "24:00")],
            "saturday": [("00:00", "24:00")],
            "sunday": [("00:00", "24:00")],
        }
    }


def _is_time_in_timeperiod(
    current_time: str,
    time_tuple_list: Sequence[tuple[str, str]],
) -> bool:
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

    days: list[Weekday] = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    current_datetime = datetime.fromtimestamp(timestamp, tzlocal())
    current_time = current_datetime.strftime("%H:%M")
    if _is_timeperiod_excluded_via_exception(
        timeperiod_definition,
        days,
        current_time,
    ):
        return False

    if (weekday := days[current_datetime.weekday()]) in timeperiod_definition:
        time_ranges = timeperiod_definition[weekday]
        assert is_time_range_list(time_ranges)
        return _is_time_in_timeperiod(current_time, time_ranges)

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


def _is_timeperiod_excluded_via_exception(
    timeperiod_definition: TimeperiodSpec,
    days: Sequence[Weekday],
    current_time: str,
) -> bool:
    for key, value in timeperiod_definition.items():
        if key in [*days, "alias", "exclude"]:
            continue

        try:
            datetime.strptime(key, "%Y-%m-%d")
        except ValueError:
            continue

        if not is_time_range_list(value):
            continue

        if _is_time_in_timeperiod(current_time, value):
            return True

    return False
