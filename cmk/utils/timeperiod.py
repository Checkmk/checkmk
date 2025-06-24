#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from pathlib import Path
from typing import TypeAlias

from dateutil.tz import tzlocal

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.store as store
from cmk.utils.caching import cache_manager
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
TimeperiodSpecs = dict[TimeperiodName, TimeperiodSpec]


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


def load_timeperiods() -> TimeperiodSpecs:
    timeperiods = store.load_from_mk_file(_get_timeperiods_conf_file_path(), "timeperiods", {})
    timeperiods.update(builtin_timeperiods())
    return timeperiods


def _get_timeperiods_conf_file_path() -> Path:
    return Path(cmk.utils.paths.check_mk_config_dir, "wato", "timeperiods.mk")


# TODO improve typing of time_tuple_list, it's a list[tuple[str, str]]
def _is_time_in_timeperiod(
    current_datetime: datetime,
    time_tuple_list: str | list[str] | list[tuple[str, str]],
    current_day: datetime | None = None,
) -> bool:
    current_time = current_datetime.strftime("%H:%M")
    if current_day and current_day.date() != current_datetime.date():
        return False
    for start, end in time_tuple_list:  # type: ignore[misc]
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

    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    current_datetime = datetime.fromtimestamp(timestamp, tzlocal())
    if _is_timeperiod_excluded_via_exception(
        timeperiod_definition,
        days,
        current_datetime,
    ):
        return False

    if (weekday := days[current_datetime.weekday()]) in timeperiod_definition:
        return _is_time_in_timeperiod(current_datetime, timeperiod_definition[weekday])

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
    days: list[str],
    current_time: datetime,
) -> bool:
    for key, value in timeperiod_definition.items():
        if key in days + ["alias", "exclude"]:
            continue

        try:
            day = datetime.strptime(key, "%Y-%m-%d")
        except ValueError:
            continue

        if not _is_time_in_timeperiod(current_time, value, day):
            return True

    return False
