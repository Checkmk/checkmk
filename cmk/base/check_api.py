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
from collections.abc import Callable
from typing import Any, Literal, Union

import cmk.utils.debug as _debug

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.http_proxy_config import HTTPProxyConfig
from cmk.utils.metrics import MetricName
from cmk.utils.regex import regex as regex  # pylint: disable=unused-import

from cmk.checkengine.checkresults import state_markers as state_markers
from cmk.checkengine.plugin_contexts import host_name as _internal_host_name
from cmk.checkengine.plugin_contexts import service_description
from cmk.checkengine.submitters import ServiceDetails, ServiceState

import cmk.base.config as _config
import cmk.base.item_state as _item_state
import cmk.base.prediction as _prediction
from cmk.base.api.agent_based import render as _render

# pylint: disable=unused-import
from cmk.base.api.agent_based.register.utils_legacy import (
    LegacyCheckDefinition as LegacyCheckDefinition,
)

# pylint: enable=unused-import

Warn = Union[None, int, float]
Crit = Union[None, int, float]
_Bound = Union[None, int, float]
Levels = tuple  # Has length 2 or 4

_MetricTuple = tuple[
    MetricName,
    float,
    Warn,
    Crit,
    _Bound,
    _Bound,
]

ServiceCheckResult = tuple[ServiceState, ServiceDetails, list[_MetricTuple]]


def host_name() -> str:
    """compatibility for making HostName a own class
    if somebody make type comparision to str or some other weird stuff we want to be compatible"""
    return str(_internal_host_name())


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
    return _render.timespan(seconds) if seconds >= 0 else f"-{_render.timespan(-seconds)}"


def get_bytes_human_readable(
    bytes_: int,
    base: Literal[1000, 1024] = 1024,
    precision: object = None,  # for legacy compatibility
    unit: str = "B",
) -> str:
    if not (
        renderer := {
            1000: _render.disksize,
            1024: _render.bytes,
        }.get(int(base))
    ):
        raise ValueError(f"Unsupported value for 'base' in get_bytes_human_readable: {base=}")
    return renderer(bytes_)[:-1] + unit


def get_filesize_human_readable(size: float) -> str:
    """Format size of a file for humans.

    Similar to get_bytes_human_readable, but optimized for file
    sizes. Really only use this for files. We assume that for smaller
    files one wants to compare the exact bytes of a file, so the
    threshold to show the value as MB/GB is higher as the one of
    get_bytes_human_readable()."""
    if size < 4 * 1024 * 1024:
        return "%d B" % int(size)
    if size < 4 * 1024 * 1024 * 1024:
        return "%.2f MB" % (float(size) / (1024 * 1024))
    return "%.2f GB" % (float(size) / (1024 * 1024 * 1024))


def get_timestamp_human_readable(timestamp: float) -> str:
    """Format a time stamp for humans in "%Y-%m-%d %H:%M:%S" format.
    In case None is given or timestamp is 0, it returns "never"."""
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    return "never"


#
# Counter handling
#

set_item_state = _item_state.set_item_state
get_item_state = _item_state.get_item_state
clear_item_state = _item_state.clear_item_state

get_rate = _item_state.get_rate

SKIP = _item_state.SKIP
RAISE = _item_state.RAISE


def _normalize_levels(levels: Levels) -> Levels:
    if len(levels) == 2:  # upper warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = None, None

    else:  # upper and lower warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = levels[2], levels[3]

    return warn_upper, crit_upper, warn_lower, crit_lower


def _do_check_levels(
    value: int | float, levels: Levels, human_readable_func: Callable, unit_info: str
) -> tuple[ServiceState, ServiceDetails]:
    warn_upper, crit_upper, warn_lower, crit_lower = _normalize_levels(levels)
    # Critical cases
    if crit_upper is not None and value >= crit_upper:
        return 2, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func, unit_info)
    if crit_lower is not None and value < crit_lower:
        return 2, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func, unit_info)

    # Warning cases
    if warn_upper is not None and value >= warn_upper:
        return 1, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func, unit_info)
    if warn_lower is not None and value < warn_lower:
        return 1, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func, unit_info)
    return 0, ""


def _levelsinfo_ty(
    ty: str, warn: Warn, crit: Crit, human_readable_func: Callable, unit_info: str
) -> str:
    warn_str = "never" if warn is None else f"{human_readable_func(warn)}{unit_info}"
    crit_str = "never" if crit is None else f"{human_readable_func(crit)}{unit_info}"
    return f" (warn/crit {ty} {warn_str}/{crit_str})"


def _build_perfdata(
    dsname: None | MetricName,
    value: int | float,
    scale_value: Callable,
    levels: Levels,
    boundaries: tuple | None,
    ref_value: None | int | float = None,
) -> list:
    if not dsname:
        return []

    perf_list = [dsname, value, levels[0], levels[1]]
    if isinstance(boundaries, tuple) and len(boundaries) == 2:
        perf_list.extend([scale_value(v) for v in boundaries])
    perfdata = [tuple(perf_list)]
    if ref_value:
        perfdata.append(("predict_" + dsname, ref_value))
    return perfdata


def check_levels(  # pylint: disable=too-many-branches
    value: int | float,
    dsname: None | MetricName,
    params: Any,
    unit: str = "",
    factor: int | float = 1.0,
    scale: int | float = 1.0,
    statemarkers: bool = False,
    human_readable_func: Callable | None = None,
    infoname: str | None = None,
    boundaries: tuple | None = None,
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
    factor:  the levels are multiplied with this factor before applying
             them to the value. This is being used for the CPU load check
             currently. The levels here are "per CPU", so the number of
             CPUs is used as factor.
    scale:   Scale of the levels in relation to "value" and the value in the RRDs.
             For example if the levels are specified in GB and the RRD store KB, then
             the scale is 1024*1024.
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

    def default_human_readable_func(x: float) -> str:
        return "%.2f" % (x / scale)

    if human_readable_func is None:
        human_readable_func = default_human_readable_func

    def scale_value(v: None | int | float) -> None | int | float:
        if v is None:
            return None
        return v * factor * scale

    infotext = f"{human_readable_func(value)}{unit_info}"
    if infoname:
        infotext = f"{infoname}: {infotext}"

    # {}, (), None, (None, None), (None, None, None, None) -> do not check any levels
    if not params or set(params) <= {None}:
        # always add warn/crit, because the call-site may not know it passed None,
        # and therefore expect a quadruple.
        perf = _build_perfdata(dsname, value, scale_value, (None, None), boundaries)
        return 0, infotext, perf

    # Pair of numbers -> static levels
    if isinstance(params, tuple):
        levels = tuple(scale_value(v) for v in _normalize_levels(params))
        ref_value = None

    # Dictionary -> predictive levels
    else:
        if not dsname:
            raise TypeError("Metric name is empty/None")

        try:
            ref_value, levels = _prediction.get_levels(
                _internal_host_name(),
                service_description(),
                dsname,
                params,
                "MAX",
                levels_factor=factor * scale,
            )
            if ref_value:
                predictive_levels_msg = "predicted reference: %s" % human_readable_func(ref_value)
            else:
                predictive_levels_msg = "no reference for prediction yet"

        except MKGeneralException as e:
            ref_value = None
            levels = (None, None, None, None)
            predictive_levels_msg = "no reference for prediction (%s)" % e

        except Exception as e:
            if _debug.enabled():
                raise
            return 3, "%s" % e, []

        if predictive_levels_msg:
            infotext += " (%s)" % predictive_levels_msg

    state, levelstext = _do_check_levels(value, levels, human_readable_func, unit_info)
    infotext += levelstext
    if statemarkers:
        infotext += state_markers[state]

    perfdata = _build_perfdata(dsname, value, scale_value, levels, boundaries, ref_value)

    return state, infotext, perfdata


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
