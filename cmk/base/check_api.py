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

"""  # pylint: disable=pointless-string-statement

# NOTE: The above suppression is necessary because our testing framework blindly
# concatenates lots of files, including this one.

# We import several modules here for the checks

# TODO: Move imports directly to checks?
import collections  # noqa: F401 # pylint: disable=unused-import
import enum  # noqa: F401 # pylint: disable=unused-import
import functools
import re  # noqa: F401 # pylint: disable=unused-import
import socket
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import Any, Literal, Union

import cmk.utils as _cmk_utils
import cmk.utils.debug as _debug
import cmk.utils.paths as _paths

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.http_proxy_config import HTTPProxyConfig
from cmk.utils.regex import regex  # noqa: F401 # pylint: disable=unused-import
from cmk.utils.type_defs import HostName, MetricName
from cmk.utils.type_defs import SectionName as _SectionName
from cmk.utils.type_defs import ServiceDetails, ServiceState, state_markers

from cmk.snmplib.type_defs import SpecialColumn as _SpecialColumn

from cmk.checkengine.plugin_contexts import check_type
from cmk.checkengine.plugin_contexts import (
    host_name as _internal_host_name,  # pylint: disable=unused-import
)
from cmk.checkengine.plugin_contexts import service_description

import cmk.base.api.agent_based.register as _agent_based_register
import cmk.base.config as _config
import cmk.base.item_state as _item_state
import cmk.base.prediction as _prediction
from cmk.base.api.agent_based import render as _render
from cmk.base.api.agent_based.checking_classes import (  # noqa: F401 # pylint: disable=unused-import
    IgnoreResultsError as MKCounterWrapped,
)
from cmk.base.api.agent_based.register.utils_legacy import (  # noqa: F401 # pylint: disable=unused-import
    LegacyCheckDefinition,
)
from cmk.base.api.agent_based.section_classes import OIDBytes as _OIDBytes
from cmk.base.api.agent_based.section_classes import OIDCached as _OIDCached

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


# backwards compatibility: allow to pass integer.
def BINARY(x: str | int) -> _OIDBytes:
    return _OIDBytes(str(x))


def CACHED_OID(x: str | int) -> _OIDCached:
    return _OIDCached(str(x))


OID_BIN = _SpecialColumn.BIN
OID_STRING = _SpecialColumn.STRING
OID_END = _SpecialColumn.END
OID_END_BIN = _SpecialColumn.END_BIN
OID_END_OCTET_STRING = _SpecialColumn.END_OCTET_STRING


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


def get_nic_speed_human_readable(bits_per_sec: float | str) -> str:
    return _render.nicspeed(float(bits_per_sec) / 8)


def get_percent_human_readable(
    percentage: float,
    scientific_notation: object = None,  # for legacy compatibility
) -> str:
    return _render.percent(percentage)


def get_number_with_precision(
    v: float,
    base: object = None,  # for legacy compatibility
    precision: int = 2,
    drop_zeroes: object = None,  # for legacy compatibility
    unit: str = "",
    zero_non_decimal: object = None,  # for legacy compatibility
) -> str:
    """
    >>> get_number_with_precision(123.4324)
    '123.43'
    >>> get_number_with_precision(2.3e5, precision=3, unit='V')
    '230000.000 V'
    """
    return "%.*f" % (precision, v) + f"{' ' if unit else ''}{unit}"


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


def get_relative_date_human_readable(timestamp: float) -> str:
    """Formats the given timestamp for humans "in ..." for future times
    or "... ago" for past timestamps."""
    now = time.time()
    if timestamp > now:
        return "in " + get_age_human_readable(timestamp - now)
    return get_age_human_readable(now - timestamp) + " ago"


#
# Counter handling
#

set_item_state = _item_state.set_item_state
get_item_state = _item_state.get_item_state
clear_item_state = _item_state.clear_item_state

get_rate = _item_state.get_rate
get_average = _item_state.get_average

SKIP = _item_state.SKIP
RAISE = _item_state.RAISE
ZERO = _item_state.ZERO


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


def get_agent_data_time() -> float | None:
    """Use this function to get the age of the agent data cache file
    of tcp or snmp hosts or None in case of piggyback data because
    we do not exactly know the latest agent data. Maybe one time
    we can handle this. For cluster hosts an exception is raised."""
    return _agent_cache_file_age(_internal_host_name(), check_type())


def _agent_cache_file_age(
    hostname: HostName,
    check_plugin_name: str,
) -> float | None:
    config_cache = _config.get_config_cache()
    if config_cache.is_cluster(hostname):
        raise MKGeneralException("get_agent_data_time() not valid for cluster")

    # NOTE: This is a workaround for the 'old' API and will not be correct
    # for the new one. This is a check plugin name, and the property of being
    # 'TCP' or 'SNMP' is a property of the section.
    # This function is deprecated for new plugins.
    # For old-style plugins, plugin and section name are same, so check the
    # corresponding section:
    section_name_str = _cmk_utils.check_utils.section_name_of(check_plugin_name)
    section = _agent_based_register.get_section_plugin(_SectionName(section_name_str))
    if hasattr(section, "trees"):
        cachefile = f"{_paths.tcp_cache_dir}/{hostname}.{section_name_str}"
    else:
        cachefile = f"{_paths.tcp_cache_dir}/{hostname}"

    with suppress(FileNotFoundError):
        return _cmk_utils.cachefile_age(cachefile)

    return None


def get_parsed_item_data(check_function: Callable) -> Callable:
    """Use this decorator to determine the parsed item data outside
    of the respective check function.

    The check function can hence be defined as follows:

    @get_parsed_item_data
    def check_<check_name>(item, params, data):
        ...

    In case of parsed not being a dict the decorator returns 3
    (unknown state) with a wrong usage message.
    In case of item not existing as a key in parsed or parsed[item]
    evaluating to False the decorator gives an empty return leading to
    cmk.base returning 3 (unknown state) with an item not found message
    (see cmk/base/agent_based/checking.py).

    WATCH OUT:
    This will not work if valid item data evaluates to False (such as a
    sensor reading that is 0.0, for example).
    """
    # ^- However: It's been like this for a while and some plugins rely on this
    # behaviour. Since this function has no counterpart in the new check API,
    # we leave it as it is.

    @functools.wraps(check_function)
    def wrapped_check_function(item: str, params: Any, parsed: Any) -> Any:
        # TODO
        if not isinstance(parsed, dict):
            return (
                3,
                "Wrong usage of decorator function 'get_parsed_item_data': parsed is not a dict",
            )
        if item not in parsed or not parsed[item]:
            return None
        return check_function(item, params, parsed[item])

    return wrapped_check_function


def validate_filter(filter_function: Any) -> Callable:
    """Validate function argument is a callable and return it"""
    if callable(filter_function):
        return filter_function
    if filter_function is None:
        return lambda *entry: entry[0]
    raise ValueError(
        f"Filtering function is not a callable, a {type(filter_function)} has been given."
    )


def discover(
    selector: Callable | None = None, default_params: None | dict[Any, Any] | str = None
) -> Callable:
    """Helper function to assist with service discoveries

    The discovery function is in many cases just a boilerplate function to
    recognize services listed in your parsed dictionary or the info
    list. It in general looks like

        def inventory_check(parsed):
            for key, value in parsed.items():
                if some_condition_based_on(key, value):
                    yield key, parameters


    The idea of this helper is to allow you only to worry about the logic
    function that decides if an entry is a service to be discovered or not.


    Keyword Arguments:
    selector       -- Filtering function (default lambda entry: entry[0])
        Default: Uses the key or first item of info variable
    default_params -- Default parameters for discovered items (default {})

    Possible uses:

        If your discovery function recognizes every entry of your parsed
        dictionary or every row of the info list as a service, then you
        just need to call discover().

            check_info["chk"] = {'inventory_function': discover()}

        In case you want to have a simple filter function when dealing with
        the info list, you can directly give a lambda function. If this
        function returns a Boolean the first item of every entry is taken
        as the service name, if the function returns a string that will be
        taken as the service name. For this example we discover as services
        entries where item3 is positive and name the service according to
        item2.

            check_info["chk"] = {'inventory_function': discover(selector=lambda line: line[2] if line[3]>0 else False)}

        In case you have a more complicated selector condition and also
        want to include default parameters you may use a decorator.

        Please note: that this discovery function does not work with the
        whole parsed/info data but only implements the logic for selecting
        each individual entry as a service.

        In the next example, we will process each entry of the parsed data
        dictionary. Use as service name the capitalized key when the
        corresponding value has certain keywords.

            @discover(default_params="the_check_default_levels")
            def inventory_thecheck(key, value):
                required_entries = ["used", "ready", "total", "uptime"]
                if all(data in value for data in required_entries):
                    return key.upper()

            check_info["chk"] = {'inventory_function': inventory_thecheck}
    """

    def _discovery(filter_function: Callable) -> Callable:
        @functools.wraps(filter_function)
        def discoverer(
            parsed: dict[Any, Any] | list[Any] | tuple
        ) -> Iterable[tuple[str, dict[Any, Any] | str]]:
            params = default_params if isinstance(default_params, (str, dict)) else {}
            if isinstance(parsed, dict):
                filterer = validate_filter(filter_function)
                for key, value in parsed.items():
                    for n in _get_discovery_iter(
                        filterer(key, value),
                        lambda: key,  # pylint: disable=cell-var-from-loop
                    ):
                        yield (n, params)
            elif isinstance(parsed, (list, tuple)):
                filterer = validate_filter(filter_function)
                for entry in parsed:
                    for n in _get_discovery_iter(
                        filterer(entry),
                        lambda: entry[0],  # pylint: disable=cell-var-from-loop
                    ):
                        yield (n, params)
            else:
                raise ValueError(
                    "Discovery function only works with dictionaries, lists, and tuples you gave a {}".format(
                        type(parsed)
                    )
                )

        return discoverer

    if callable(selector):
        return _discovery(selector)

    if selector is None and default_params is None:
        return _discovery(lambda *args: args[0])

    return _discovery


def _get_discovery_iter(name: Any, get_name: Callable[[], str]) -> Iterable[str]:
    if isinstance(name, str):
        return iter((name,))
    if name is True:
        return iter((get_name(),))
    try:
        return iter(name)
    except TypeError:
        return iter(())


# NOTE: Currently this is not really needed, it is just here to keep any start
# import in sync with our intended API.
__all__ = list(get_check_api_context())
