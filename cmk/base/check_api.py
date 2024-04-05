#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The things in this module specify the old Check_MK (<- see? Old!) check API

+---------------------------------------------------------------------------+
|             THIS API IS OLD, AND NO LONGER MAINTAINED.                    |
|                                                                           |
| All new plugins should be programmed against the new API, please refer to |
| the online user manual for details!                                       |
|                                                                           |
+---------------------------------------------------------------------------+

"""

import socket
import time
from collections.abc import Callable, Mapping
from typing import Any, Generator, Literal

import cmk.utils.debug as _debug

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
from cmk.utils.hostaddress import HostName
from cmk.utils.http_proxy_config import HTTPProxyConfig
from cmk.utils.metrics import MetricName
from cmk.utils.regex import regex as regex  # pylint: disable=unused-import

# pylint: disable=unused-import
from cmk.checkengine.checkresults import state_markers as state_markers
from cmk.checkengine.submitters import ServiceDetails, ServiceState

import cmk.base.config as _config

# pylint: disable=unused-import
from cmk.base.api.agent_based.register.utils_legacy import (
    LegacyCheckDefinition as LegacyCheckDefinition,
)
from cmk.base.plugin_contexts import host_name as host_name  # pylint: disable=unused-import
from cmk.base.plugin_contexts import service_description  # pylint: disable=unused-import

from cmk.agent_based import v1 as _v1

# pylint: enable=unused-import

Warn = None | int | float
Crit = None | int | float
_Bound = None | int | float
Levels = tuple  # Has length 2 or 4

_MetricTuple = (
    tuple[str, float]
    | tuple[str, float, Warn, Crit]
    | tuple[str, float, Warn, Crit, _Bound, _Bound]
)

ServiceCheckResult = tuple[ServiceState, ServiceDetails, list[_MetricTuple]]


# to ease migration:
DiscoveryResult = Generator[tuple[str | None, Mapping[str, object]], None, None]
CheckResult = Generator[tuple[int, str] | tuple[int, str, list[_MetricTuple]], None, None]


# to ease migration:
def Service(
    *, item: str | None = None, parameters: Mapping[str, object] | None = None
) -> tuple[str | None, Mapping[str, object]]:
    return item, parameters or {}


def get_check_api_context() -> _config.CheckContext:
    """This is called from cmk.base code to get the Check API things. Don't
    use this from checks."""
    return {k: v for k, v in globals().items() if not k.startswith("_")}


# .
#   .--Check API-----------------------------------------------------------.
#   |             ____ _               _         _    ____ ___             |
#   |            / ___| |__   ___  ___| | __    / \  |  _ \_ _|            |
#   |           | |   | '_ \ / _ \/ __| |/ /   / _ \ | |_) | |             |
#   |           | |___| | | |  __/ (__|   <   / ___ \|  __/| |             |
#   |            \____|_| |_|\___|\___|_|\_\ /_/   \_\_|  |___|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper API for being used in checks                                 |
#   '----------------------------------------------------------------------'


def saveint(i: Any) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def savefloat(f: Any) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def is_ipv6_primary(hostname: HostName) -> bool:
    return _config.get_config_cache().default_address_family(hostname) is socket.AF_INET6


def get_age_human_readable(seconds: float) -> str:
    return _v1.render.timespan(seconds) if seconds >= 0 else f"-{_v1.render.timespan(-seconds)}"


def get_bytes_human_readable(
    bytes_: int,
    base: Literal[1000, 1024] = 1024,
    precision: object = None,  # for legacy compatibility
    unit: str = "B",
) -> str:
    if not (
        renderer := {
            1000: _v1.render.disksize,
            1024: _v1.render.bytes,
        }.get(int(base))
    ):
        raise ValueError(f"Unsupported value for 'base' in get_bytes_human_readable: {base=}")
    return renderer(bytes_)[:-1] + unit


def get_timestamp_human_readable(timestamp: float) -> str:
    """Format a time stamp for humans in "%Y-%m-%d %H:%M:%S" format.
    In case None is given or timestamp is 0, it returns "never"."""
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    return "never"


def _normalize_levels(levels: Levels) -> Levels:
    if len(levels) == 2:  # upper warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = None, None

    else:  # upper and lower warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = levels[2], levels[3]

    return warn_upper, crit_upper, warn_lower, crit_lower


def _do_check_levels(
    value: int | float, levels: Levels, human_readable_func: Callable
) -> tuple[ServiceState, ServiceDetails]:
    warn_upper, crit_upper, warn_lower, crit_lower = _normalize_levels(levels)
    # Critical cases
    if crit_upper is not None and value >= crit_upper:
        return 2, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func)
    if crit_lower is not None and value < crit_lower:
        return 2, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func)

    # Warning cases
    if warn_upper is not None and value >= warn_upper:
        return 1, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func)
    if warn_lower is not None and value < warn_lower:
        return 1, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func)
    return 0, ""


def _levelsinfo_ty(ty: str, warn: Warn, crit: Crit, human_readable_func: Callable) -> str:
    warn_str = "never" if warn is None else f"{human_readable_func(warn)}"
    crit_str = "never" if crit is None else f"{human_readable_func(crit)}"
    return f" (warn/crit {ty} {warn_str}/{crit_str})"


def _build_perfdata(
    dsname: None | MetricName,
    value: int | float,
    levels: Levels,
    boundaries: tuple | None,
) -> list:
    if not dsname:
        return []
    used_boundaries = boundaries if isinstance(boundaries, tuple) and len(boundaries) == 2 else ()
    return [(dsname, value, levels[0], levels[1], *used_boundaries)]


def check_levels(  # pylint: disable=too-many-branches
    value: int | float,
    dsname: None | MetricName,
    params: Any,
    unit: str = "",
    human_readable_func: Callable | None = None,
    infoname: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
) -> ServiceCheckResult:
    """Generic function for checking a value against levels

    This also supports predictive levels.

    value:   currently measured value
    dsname:  name of the datasource in the RRD that corresponds to this value
             or None in order to skip perfdata
    params:  None or Tuple(None, None) -> no level checking.
             Tuple variants with non-None values:
             Tuple[warn_upper, crit_upper] -> upper level checking only.
             Tuple[warn_upper, crit_upper, warn_lower, crit_lower]
             -> upper and lower level checking.
             If a Dict is passed to check_levels, predictive levels are used
             automatically. The following constellations are possible:
             Dict containing "lower" as key -> lower level checking.
             Dict containing "upper" or "levels_upper_min" as key -> upper level checking.
             Dict containing "lower" and "upper"/"levels_upper_min" as key ->
             lower and upper level checking.
    unit:    unit to be displayed in the plugin output.
             Be aware: if a (builtin) human_readable_func is stated which already
             provides a unit info, then this unit is not necessary. An additional
             unit info is useful if a rate is calculated, eg.
                unit="/s",
                human_readable_func=get_bytes_human_readable,
             results in 'X B/s'.
    human_readable_func: Single argument function to present in a human readable fashion
                         the value. Builtin human_readable-functions already provide a unit:
                         - get_percent_human_readable
                         - get_age_human_readable
                         - get_bytes_human_readable
                         - get_filesize_human_readable
                         - get_nic_speed_human_readable
                         - get_timestamp_human_readable
                         - get_relative_date_human_readable
    infoname: Perf value name for infotext like a title.
    boundaries: Add minimum and maximum to performance data.
    """
    if unit.startswith("/"):
        unit_info: str = unit
    elif unit:
        unit_info = " %s" % unit
    else:
        unit_info = ""

    if human_readable_func is None:

        def render_func(x: float) -> str:
            return "%.2f%s" % (x, unit_info)

    else:

        def render_func(x: float) -> str:
            return "%s%s" % (human_readable_func(x), unit_info)

    if params and isinstance(params, dict):
        if not dsname:
            raise TypeError("Metric name is empty/None")
        result, *metrics = _v1.check_levels_predictive(
            value,
            levels=params,
            metric_name=dsname,
            render_func=render_func,
            label=infoname,
            boundaries=boundaries,
        )
        assert isinstance(result, _v1.Result)
        return (
            int(result.state),
            result.summary,
            [
                (m.name, m.value, *m.levels, *m.boundaries)
                for m in metrics
                if isinstance(m, _v1.Metric)
            ],
        )

    infotext = f"{render_func(value)}"
    if infoname:
        infotext = f"{infoname}: {infotext}"

    # normalize {}, (), None, (None, None), (None, None, None, None)
    if not params or set(params) <= {None}:
        levels: Levels = (None, None, None, None)
    else:
        levels = _normalize_levels(params)

    state, levelstext = _do_check_levels(value, levels, render_func)
    return state, infotext + levelstext, _build_perfdata(dsname, value, levels, boundaries)


def passwordstore_get_cmdline(fmt: str, pw: tuple | str) -> str | tuple[str, str, str]:
    """Use this to prepare a command line argument for using a password from the
    Check_MK password store or an explicitly configured password."""
    if not isinstance(pw, tuple):
        pw = ("password", pw)

    if pw[0] == "password":
        return fmt % pw[1]

    return ("store", pw[1], fmt)


def get_http_proxy(http_proxy: tuple[str, str]) -> HTTPProxyConfig:
    """Returns a proxy config object to be used for HTTP requests

    Intended to receive a value configured by the user using the HTTPProxyReference valuespec.
    """
    return _config.get_http_proxy(http_proxy)


# NOTE: Currently this is not really needed, it is just here to keep any start
# import in sync with our intended API.
__all__ = list(get_check_api_context())
