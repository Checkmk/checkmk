#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypeAlias

import livestatus

import cmk.utils.cleanup
import cmk.utils.debug
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.exceptions import MKTimeout

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
    return _config_cache.get("timeperiods_cache").get(timeperiod, True)


def timeperiod_active(timeperiod: TimeperiodName) -> bool | None:
    """Returns
    True : active
    False: inactive
    None : unknown timeperiod

    Raises an exception if e.g. a timeout or connection error appears.
    This way errors can be handled upstream."""
    update_timeperiods_cache()
    return _config_cache.get("timeperiods_cache").get(timeperiod)


def update_timeperiods_cache() -> None:
    # { "last_update": 1498820128, "timeperiods": [{"24x7": True}] }
    # The value is store within the config cache since we need a fresh start on reload
    tp_cache = _config_cache.get("timeperiods_cache")

    if not tp_cache:
        connection = livestatus.LocalConnection()
        connection.set_timeout(2)
        response = connection.query("GET timeperiods\nColumns: name in")
        for tp_name, tp_active in response:
            tp_cache[tp_name] = bool(tp_active)


def cleanup_timeperiod_caches() -> None:
    _config_cache.get("timeperiods_cache").clear()


cmk.utils.cleanup.register_cleanup(cleanup_timeperiod_caches)
