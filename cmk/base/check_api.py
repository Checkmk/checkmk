#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The things in this module specify the official Check_MK check API. Meaning all
variables, functions etc. and default modules that are available to checks.

Modules available by default (pre imported by Check_MK):
    collections
    enum
    fnmatch
    functools
    math
    os
    re
    socket
    sys
    time
    pprint

Global variables:
    from cmk.utils.regex import regex
    import cmk.utils.render as render
    core_state_names     Names of states. Usually used to convert numeric states
                         to their name for adding it to the plugin output.
                         The mapping is like this:

                           -1: 'PEND'
                            0: 'OK'
                            1: 'WARN'
                            2: 'CRIT'
                            3: 'UNKN'

    state_markers        Symbolic representations of states in plugin output.
                         Will be displayed colored by the Check_MK GUI.
                         The mapping is like this:

                            0: ''
                            1: '(!)'
                            2: '(!!)'
                            3: '(?)'

    nagios_illegal_chars Characters not allowed to be used in service
                         descriptions. Can be used in discovery functions to
                         remove unwanted characters from a string. The unwanted
                         chars default are: `;~!$%^&*|\'"<>?,()=


    OID_BIN              TODO
    OID_END              TODO
    OID_END_BIN          TODO
    OID_END_OCTET_STRING TODO
    OID_STRING           TODO

    MGMT_ONLY            Check is only executed for management boards.
    HOST_PRECEDENCE      Use host address/credentials eg. when it's a SNMP HOST.
    HOST_ONLY            Check is only executed for real SNMP hosts.

    RAISE                Used as value for the "onwrap" argument of the get_rate()
                         function. See get_rate() documentation for details
    SKIP                 Used as value for the "onwrap" argument of the get_rate()
                         function. See get_rate() documentation for details
    ZERO                 Used as value for the "onwrap" argument of the get_rate()
                         function. See get_rate() documentation for details
"""  # pylint: disable=pointless-string-statement

# NOTE: The above suppression is necessary because our testing framework blindly
# concatenates lots of files, including this one.

# We import several modules here for the checks

# TODO: Move imports directly to checks?
from __future__ import division  # pylint: disable=misplaced-future
import collections  # noqa: F401 # pylint: disable=unused-import
import enum  # noqa: F401 # pylint: disable=unused-import
import fnmatch  # noqa: F401 # pylint: disable=unused-import
import functools
import math  # noqa: F401 # pylint: disable=unused-import
import os
import re  # noqa: F401 # pylint: disable=unused-import
import socket  # noqa: F401 # pylint: disable=unused-import
import sys  # pylint: disable=unused-import
import time
# NOTE: We do not use pprint in this module, but it is part of the check API.
import pprint  # noqa: F401 # pylint: disable=unused-import
import calendar

from typing import (  # pylint: disable=unused-import
    Any, Callable, Dict, Iterable, List, Optional, Set, Text, Tuple, Union,
)

import six

import cmk.utils.debug as _debug
import cmk.utils.defines as _defines
import cmk.utils.paths as _paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.regex import regex  # noqa: F401 # pylint: disable=unused-import
import cmk.utils.render as render
import cmk.utils.rulesets.tuple_rulesets as _tuple_rulesets

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
import cmk.utils as _cmk_utils
import cmk.base.config as _config
import cmk.base.console as _console  # noqa: F401 # pylint: disable=unused-import
import cmk.base.snmp_utils as _snmp_utils
import cmk.base.item_state as _item_state
import cmk.base.prediction as _prediction
import cmk.base.check_api_utils as _check_api_utils
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, ServiceName, CheckPluginName, MetricName,
)
from cmk.base.check_utils import (  # pylint: disable=unused-import
    ServiceState, ServiceDetails, ServiceCheckResult,
)

Warn = Union[None, int, float]
Crit = Union[None, int, float]
Levels = Tuple  # Has length 2 or 4


def get_check_api_context():
    # type: () -> _config.CheckContext
    """This is called from cmk.base code to get the Check API things. Don't
    use this from checks."""
    return {k: v for k, v in globals().items() if not k.startswith("_")}


#.
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

# Names of texts usually output by checks
core_state_names = _defines.short_service_state_names()

# Symbolic representations of states in plugin output
state_markers = _check_api_utils.state_markers

# backwards compatibility: allow to pass integer.
BINARY = lambda x: _snmp_utils.OIDBytes(str(x))
CACHED_OID = lambda x: _snmp_utils.OIDCached(str(x))

OID_END = _snmp_utils.OID_END
OID_STRING = _snmp_utils.OID_STRING
OID_BIN = _snmp_utils.OID_BIN
OID_END_BIN = _snmp_utils.OID_END_BIN
OID_END_OCTET_STRING = _snmp_utils.OID_END_OCTET_STRING
binstring_to_int = _snmp_utils.binstring_to_int

# Management board checks
MGMT_ONLY = _check_api_utils.MGMT_ONLY  # Use host address/credentials when it's a SNMP HOST
HOST_PRECEDENCE = _check_api_utils.HOST_PRECEDENCE  # Check is only executed for mgmt board (e.g. Managegment Uptime)
HOST_ONLY = _check_api_utils.HOST_ONLY  # Check is only executed for real SNMP host (e.g. interfaces)

host_name = _check_api_utils.host_name
service_description = _check_api_utils.service_description
check_type = _check_api_utils.check_type

from cmk.base.discovered_labels import (  # noqa: F401 # pylint: disable=unused-import
    DiscoveredServiceLabels as ServiceLabels, ServiceLabel, DiscoveredHostLabels as HostLabels,
    HostLabel,
)
Service = _check_api_utils.Service

network_interface_scan_registry = _snmp_utils.MutexScanRegistry()


def saveint(i):
    # type: (Any) -> int
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def savefloat(f):
    # type: (Any) -> float
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


class as_float(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __repr__(self):
        # type: () -> str
        if self > sys.float_info.max:
            return '1e%d' % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return '-1e%d' % (sys.float_info.max_10_exp + 1)
        return super(as_float, self).__repr__()


# Compatibility wrapper for the pre 1.6 existant config.service_extra_conf()
def service_extra_conf(hostname, service, ruleset):
    # type: (HostName, ServiceName, _config.Ruleset) -> List
    return _config.get_config_cache().service_extra_conf(hostname, service, ruleset)


# Compatibility wrapper for the pre 1.6 existant config.host_extra_conf()
def host_extra_conf(hostname, ruleset):
    # type: (HostName, _config.Ruleset) -> List
    return _config.get_config_cache().host_extra_conf(hostname, ruleset)


# Compatibility wrapper for the pre 1.6 existant config.in_binary_hostlist()
def in_binary_hostlist(hostname, ruleset):
    # type: (HostName, _config.Ruleset) -> bool
    return _config.get_config_cache().in_binary_hostlist(hostname, ruleset)


# Compatibility wrapper for the pre 1.6 existant conf.host_extra_conf_merged()
def host_extra_conf_merged(hostname, conf):
    # type: (HostName, _config.Ruleset) -> Dict[str, Any]
    return _config.get_config_cache().host_extra_conf_merged(hostname, conf)


# TODO: Only used by logwatch check. Can we clean this up?
get_rule_options = _tuple_rulesets.get_rule_options

# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
in_extraconf_hostlist = _tuple_rulesets.in_extraconf_hostlist
hosttags_match_taglist = _tuple_rulesets.hosttags_match_taglist


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def all_matching_hosts(condition, with_foreign_hosts):
    # type: (Dict[str, Any], bool) -> Set[HostName]
    return _config.get_config_cache().ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        condition, with_foreign_hosts)


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def tags_of_host(hostname):
    # type: (HostName) -> Set[str]
    return _config.get_config_cache().get_host_config(hostname).tags


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def is_ipv6_primary(hostname):
    # type: (HostName) -> bool
    return _config.get_config_cache().get_host_config(hostname).is_ipv6_primary


nagios_illegal_chars = _config.nagios_illegal_chars
is_cmc = _config.is_cmc

get_age_human_readable = lambda secs: "%s" % render.Age(secs)
get_bytes_human_readable = render.fmt_bytes
get_nic_speed_human_readable = render.fmt_nic_speed
get_percent_human_readable = render.percent
get_number_with_precision = render.fmt_number_with_precision
quote_shell_string = _cmk_utils.quote_shell_string


def get_checkgroup_parameters(group, deflt=None):
    # type: (str, Optional[str]) -> Optional[str]
    return _config.checkgroup_parameters.get(group, deflt)


# TODO: Replace by some render.* function / move to render module?
def get_filesize_human_readable(size):
    # type: (float) -> str
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


# TODO: Replace by some render.* function / move to render module?
def get_timestamp_human_readable(timestamp):
    # type: (float) -> str
    """Format a time stamp for humans in "%Y-%m-%d %H:%M:%S" format.
    In case None is given or timestamp is 0, it returns "never"."""
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    return "never"


# TODO: Replace by some render.* function / move to render module?
def get_relative_date_human_readable(timestamp):
    # type: (float) -> str
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
get_all_item_states = _item_state.get_all_item_states
clear_item_state = _item_state.clear_item_state
clear_item_states_by_full_keys = _item_state.clear_item_states_by_full_keys
get_rate = _item_state.get_rate
get_average = _item_state.get_average
# TODO: Cleanup checks and deprecate this
last_counter_wrap = _item_state.last_counter_wrap

SKIP = _item_state.SKIP
RAISE = _item_state.RAISE
ZERO = _item_state.ZERO

MKCounterWrapped = _item_state.MKCounterWrapped


def _normalize_levels(levels):
    # type: (Levels) -> Levels
    if len(levels) == 2:  # upper warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = None, None

    else:  # upper and lower warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = levels[2], levels[3]

    return warn_upper, crit_upper, warn_lower, crit_lower


def _do_check_levels(value, levels, human_readable_func, unit_info):
    # type: (Union[int, float], Levels, Callable, Text) -> Tuple[ServiceState, ServiceDetails]
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


def _levelsinfo_ty(ty, warn, crit, human_readable_func, unit_info):
    # type: (Text, Warn, Crit, Callable, Text) -> Text
    return u" (warn/crit {0} {1}{3}/{2}{3})".format(ty, human_readable_func(warn),
                                                    human_readable_func(crit), unit_info)


def _build_perfdata(dsname, value, scale_value, levels, boundaries, ref_value=None):
    # type: (Union[None, MetricName], Union[int, float], Callable, Levels, Optional[Tuple], Union[None, int, float]) -> List
    if not dsname:
        return []

    perf_list = [dsname, value, levels[0], levels[1]]
    if isinstance(boundaries, tuple) and len(boundaries) == 2:
        perf_list.extend([scale_value(v) for v in boundaries])
    perfdata = [tuple(perf_list)]
    if ref_value:
        perfdata.append(('predict_' + dsname, ref_value))
    return perfdata


def check_levels(value,
                 dsname,
                 params,
                 unit="",
                 factor=1.0,
                 scale=1.0,
                 statemarkers=False,
                 human_readable_func=None,
                 infoname=None,
                 boundaries=None):
    # type: (Union[int, float], Union[None, MetricName], Any, Text, Union[int, float], Union[int, float], bool, Optional[Callable], Optional[Text], Optional[Tuple]) -> ServiceCheckResult
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
    if unit.startswith('/'):
        unit_info = unit  # type: Text
    elif unit:
        unit_info = " %s" % unit
    else:
        unit_info = ""

    if human_readable_func is None:
        human_readable_func = lambda x: "%.2f" % (x / scale)

    def scale_value(v):
        # type: (Union[None, int, float]) -> Union[None, int, float]
        if v is None:
            return None
        return v * factor * scale

    infotext = "%s%s" % (human_readable_func(value), unit_info)
    if infoname:
        infotext = "%s: %s" % (infoname, infotext)

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
            ref_value, levels = _prediction.get_levels(host_name(),
                                                       service_description(),
                                                       dsname,
                                                       params,
                                                       "MAX",
                                                       levels_factor=factor * scale)
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


def get_effective_service_level():
    # type: () -> ServiceState
    """Get the service level that applies to the current service.
    This can only be used within check functions, not during discovery nor parsing."""
    config_cache = _config.get_config_cache()
    service_level = config_cache.service_level_of_service(host_name(), service_description())
    if service_level is not None:
        return service_level

    service_level = config_cache.get_host_config(host_name()).service_level
    if service_level is not None:
        return service_level

    return 0


def utc_mktime(time_struct):
    # type: (time.struct_time) -> int
    """Works like time.mktime() but assumes the time_struct to be in UTC,
    not in local time."""
    return calendar.timegm(time_struct)


def passwordstore_get_cmdline(fmt, pw):
    # type: (str, Union[Tuple, str]) -> Union[str, Tuple[str, str, str]]
    """Use this to prepare a command line argument for using a password from the
    Check_MK password store or an explicitly configured password."""
    if not isinstance(pw, tuple):
        pw = ("password", pw)

    if pw[0] == "password":
        return fmt % pw[1]

    return ("store", pw[1], fmt)


def get_http_proxy(http_proxy):
    # type: (Tuple[str, str]) -> Optional[str]
    """Returns proxy URL to be used for HTTP requests

    Pass a value configured by the user using the HTTPProxyReference valuespec to this function
    and you will get back ether a proxy URL, an empty string to enforce no proxy usage or None
    to use the proxy configuration from the process environment.
    """
    return _config.get_http_proxy(http_proxy)


def get_agent_data_time():
    # type: () -> Optional[float]
    """Use this function to get the age of the agent data cache file
    of tcp or snmp hosts or None in case of piggyback data because
    we do not exactly know the latest agent data. Maybe one time
    we can handle this. For cluster hosts an exception is raised."""
    return _agent_cache_file_age(host_name(), check_type())


def _agent_cache_file_age(hostname, check_plugin_name):
    # type: (HostName, CheckPluginName) -> Optional[float]
    host_config = _config.get_config_cache().get_host_config(hostname)
    if host_config.is_cluster:
        raise MKGeneralException("get_agent_data_time() not valid for cluster")

    # TODO 'import-outside-toplevel' not available in pylint for Python 2
    import cmk.base.check_utils  # pylint: disable-all
    if cmk.base.check_utils.is_snmp_check(check_plugin_name):
        cachefile = _paths.tcp_cache_dir + "/" + hostname + "." + check_plugin_name.split(".")[
            0]  # type: Optional[str]
    elif cmk.base.check_utils.is_tcp_check(check_plugin_name):
        cachefile = _paths.tcp_cache_dir + "/" + hostname
    else:
        cachefile = None

    if cachefile is not None and os.path.exists(cachefile):
        return _cmk_utils.cachefile_age(cachefile)

    return None


def get_parsed_item_data(check_function):
    # type: (Callable) -> Callable
    """Use this decorator to determine the parsed item data outside
    of the respective check function.

    The check function can hence be defined as follows:

    @get_parsed_item_data
    def check_<check_name>(item, params, data):
        ...

    In case of parsed not being a dict the decorator returns 3
    (UNKN state) with a wrong usage message.
    In case of item not existing as a key in parsed or parsed[item]
    not existing the decorator gives an empty return leading to
    cmk.base returning 3 (UNKN state) with an item not found message
    (see cmk/base/checking.py).
    """
    @functools.wraps(check_function)
    def wrapped_check_function(item, params, parsed):
        # TODO
        # type: (Text, Any, Any) -> Any
        if not isinstance(parsed, dict):
            return 3, "Wrong usage of decorator function 'get_parsed_item_data': parsed is not a dict"
        if item not in parsed or not parsed[item]:
            return
        return check_function(item, params, parsed[item])

    return wrapped_check_function


def discover_single(info):
    # type: (Union[List, Dict]) -> Optional[List]
    """Return a discovered item in case there is info text or parsed"""
    if info:
        return [(None, {})]
    return None


def validate_filter(filter_function):
    # type: (Any) -> Callable
    """Validate function argument is a callable and return it"""
    if callable(filter_function):
        return filter_function
    if filter_function is None:
        return lambda *entry: entry[0]
    raise ValueError("Filtering function is not a callable, a {} has been given.".format(
        type(filter_function)))


def discover(selector=None, default_params=None):
    # type: (Optional[Callable], Union[None, Dict[Any, Any], str]) -> Callable
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
    def _discovery(filter_function):
        # type: (Callable) -> Callable
        @functools.wraps(filter_function)
        def discoverer(parsed):
            # type: (Union[Dict[Any, Any], List[Any], Tuple]) -> Iterable[Tuple[str, Union[Dict[Any, Any], str]]]
            params = default_params if isinstance(default_params, six.string_types +
                                                  (dict,)) else {}
            if isinstance(parsed, dict):
                filterer = validate_filter(filter_function)
                for key, value in parsed.items():
                    for n in _get_discovery_iter(filterer(key, value), lambda: key):
                        yield (n, params)
            elif isinstance(parsed, (list, tuple)):
                filterer = validate_filter(filter_function)
                for entry in parsed:
                    for n in _get_discovery_iter(filterer(entry), lambda: entry[0]):
                        yield (n, params)
            else:
                raise ValueError(
                    "Discovery function only works with dictionaries, lists, and tuples you gave a {}"
                    .format(type(parsed)))

        return discoverer

    if callable(selector):
        return _discovery(selector)

    if selector is None and default_params is None:
        return _discovery(lambda *args: args[0])

    return _discovery


def _get_discovery_iter(name, get_name):
    # type: (Any, Callable[[], str]) -> Iterable[str]
    if isinstance(name, six.string_types):
        return iter((six.ensure_str(name),))
    if name is True:
        return iter((get_name(),))
    try:
        return iter(name)
    except TypeError:
        return iter(())


# NOTE: Currently this is not really needed, it is just here to keep any start
# import in sync with our intended API.
# TODO: Do we really need this? Is there code which uses a star import for this
# module?
__all__ = list(get_check_api_context())
