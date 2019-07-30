#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
""" # # pylint: disable=pointless-string-statement

# NOTE: The above suppression is necessary because our testing framework blindly
# concatenates lots of files, including this one.

# We import several modules here for the checks

# TODO: Move imports directly to checks?
import collections  # pylint: disable=unused-import
import enum  # pylint: disable=unused-import
import fnmatch  # pylint: disable=unused-import
import functools
import math  # pylint: disable=unused-import
import os
import re  # pylint: disable=unused-import
import socket  # pylint: disable=unused-import
import sys  # pylint: disable=unused-import
import time
# NOTE: We do not use pprint in this module, but it is part of the check API.
import pprint  # pylint: disable=unused-import

from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union  # pylint: disable=unused-import

import six

import cmk.utils.debug as _debug
import cmk.utils.defines as _defines
import cmk.utils.paths as _paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.regex import regex  # pylint: disable=unused-import
import cmk.utils.render as render
import cmk.utils.rulesets.tuple_rulesets as _tuple_rulesets

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
import cmk_base.utils as _utils
import cmk_base.config as _config
import cmk_base.console as _console  # pylint: disable=unused-import
import cmk_base.snmp_utils as _snmp_utils
import cmk_base.item_state as _item_state
import cmk_base.prediction as _prediction
import cmk_base.check_api_utils as _check_api_utils


def get_check_api_context():
    """This is called from cmk_base code to get the Check API things. Don't
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

BINARY = _snmp_utils.BINARY
CACHED_OID = _snmp_utils.CACHED_OID

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

from cmk_base.discovered_labels import (  # pylint: disable=unused-import
    DiscoveredServiceLabels as ServiceLabels, ServiceLabel, DiscoveredHostLabels as HostLabels,
    HostLabel,
)
Service = _check_api_utils.Service

network_interface_scan_registry = _snmp_utils.MutexScanRegistry()


def saveint(i):
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except:
        return 0


def savefloat(f):
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except:
        return 0.0


class as_float(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __repr__(self):
        if self > sys.float_info.max:
            return '1e309'
        if self < -1 * sys.float_info.max:
            return '-1e309'
        return super(as_float, self).__repr__()


# Compatibility wrapper for the pre 1.6 existant config.service_extra_conf()
def service_extra_conf(hostname, service, ruleset):
    return _config.get_config_cache().service_extra_conf(hostname, service, ruleset)


# Compatibility wrapper for the pre 1.6 existant config.host_extra_conf()
def host_extra_conf(hostname, ruleset):
    return _config.get_config_cache().host_extra_conf(hostname, ruleset)


# Compatibility wrapper for the pre 1.6 existant config.in_binary_hostlist()
def in_binary_hostlist(hostname, ruleset):
    return _config.get_config_cache().in_binary_hostlist(hostname, ruleset)


# Compatibility wrapper for the pre 1.6 existant conf.host_extra_conf_merged()
def host_extra_conf_merged(hostname, conf):
    return _config.get_config_cache().host_extra_conf_merged(hostname, conf)


# TODO: Only used by logwatch check. Can we clean this up?
get_rule_options = _tuple_rulesets.get_rule_options

# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
in_extraconf_hostlist = _tuple_rulesets.in_extraconf_hostlist
hosttags_match_taglist = _tuple_rulesets.hosttags_match_taglist


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def all_matching_hosts(tags, hostlist, with_foreign_hosts):
    return _config.get_config_cache().ruleset_matcher.ruleset_optimizer._all_matching_hosts(
        tags, hostlist, with_foreign_hosts)


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def tags_of_host(hostname):
    return _config.get_config_cache().get_host_config(hostname).tags


# These functions were used in some specific checks until 1.6. Don't add it to
# the future check API. It's kept here for compatibility reasons for now.
def is_ipv6_primary(hostname):
    return _config.get_config_cache().get_host_config(hostname).is_ipv6_primary


nagios_illegal_chars = _config.nagios_illegal_chars
is_cmc = _config.is_cmc

get_age_human_readable = lambda secs: str(render.Age(secs))
get_bytes_human_readable = render.fmt_bytes
get_percent_human_readable = render.percent
quote_shell_string = _utils.quote_shell_string


def get_checkgroup_parameters(group, deflt=None):
    return _config.checkgroup_parameters.get(group, deflt)


# TODO: Replace by some render.* function / move to render module?
def get_filesize_human_readable(size):
    """Format size of a file for humans.

    Similar to get_bytes_human_readable, but optimized for file
    sizes. Really only use this for files. We assume that for smaller
    files one wants to compare the exact bytes of a file, so the
    threshold to show the value as MB/GB is higher as the one of
    get_bytes_human_readable()."""
    if size < 4 * 1024 * 1024:
        return "%d B" % int(size)
    elif size < 4 * 1024 * 1024 * 1024:
        return "%.2f MB" % (float(size) / (1024 * 1024))
    return "%.2f GB" % (float(size) / (1024 * 1024 * 1024))


# TODO: Replace by some render.* function / move to render module?
def get_nic_speed_human_readable(speed):
    """Format network speed (bit/s) for humans."""
    try:
        speedi = int(speed)
        if speedi == 10000000:
            speed = "10 Mbit/s"
        elif speedi == 100000000:
            speed = "100 Mbit/s"
        elif speedi == 1000000000:
            speed = "1 Gbit/s"
        elif speedi < 1500:
            speed = "%d bit/s" % speedi
        elif speedi < 1000000:
            speed = "%.1f Kbit/s" % (speedi / 1000.0)
        elif speedi < 1000000000:
            speed = "%.2f Mbit/s" % (speedi / 1000000.0)
        else:
            speed = "%.2f Gbit/s" % (speedi / 1000000000.0)
    except:
        pass
    return speed


# TODO: Replace by some render.* function / move to render module?
def get_timestamp_human_readable(timestamp):
    """Format a time stamp for humans in "%Y-%m-%d %H:%M:%S" format.
    In case None is given or timestamp is 0, it returns "never"."""
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    return "never"


# TODO: Replace by some render.* function / move to render module?
def get_relative_date_human_readable(timestamp):
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


def _normalize_bounds(levels):
    if len(levels) == 2:  # upper warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = None, None

    else:  # upper and lower warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = levels[2], levels[3]

    return warn_upper, crit_upper, warn_lower, crit_lower


def _check_boundaries(value, levels, human_readable_func, unit_info):
    warn_upper, crit_upper, warn_lower, crit_lower = _normalize_bounds(levels)
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
    return " (warn/crit {0} {1}{3}/{2}{3})".format(ty, human_readable_func(warn),
                                                   human_readable_func(crit), unit_info)


def check_levels(value,
                 dsname,
                 params,
                 unit="",
                 factor=1.0,
                 scale=1.0,
                 statemarkers=False,
                 human_readable_func=None,
                 infoname=None):
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
    """
    unit_info = ""
    if unit.startswith('/'):
        unit_info = unit
    elif unit:
        unit_info = " %s" % unit

    if human_readable_func is None:
        human_readable_func = lambda x: "%.2f" % (x / scale)

    def scale_value(v):
        if v is None:
            return None
        return v * factor * scale

    if infoname:
        infotext = "%s: %s%s" % (infoname, human_readable_func(value), unit_info)
    else:
        infotext = "%s%s" % (human_readable_func(value), unit_info)

    # {}, (), None, (None, None), (None, None, None, None) -> do not check any levels
    if not params or set(params) <= {None}:
        if dsname:
            return 0, infotext, [(dsname, value)]
        return 0, infotext, []

    # Pair of numbers -> static levels
    elif isinstance(params, tuple):
        levels = map(scale_value, _normalize_bounds(params))
        ref_value = None

    # Dictionary -> predictive levels
    else:
        try:
            ref_value, levels = \
                      _prediction.get_levels(host_name(), service_description(),
                                dsname, params, "MAX", levels_factor=factor * scale)

            if ref_value:
                predictive_levels_msg = "predicted reference: %s" % human_readable_func(ref_value)
            else:
                predictive_levels_msg = "no reference for prediction yet"

        except MKGeneralException as e:
            ref_value = None
            levels = [None, None, None, None]
            predictive_levels_msg = "no reference for prediction (%s)" % e

        except Exception as e:
            if _debug.enabled():
                raise
            return 3, "%s" % e, []

        if predictive_levels_msg:
            infotext += " (%s)" % predictive_levels_msg

    state, levelstext = _check_boundaries(value, levels, human_readable_func, unit_info)
    infotext += levelstext
    if statemarkers:
        infotext += state_markers[state]

    if dsname:
        perfdata = [(dsname, value, levels[0], levels[1])]
        if ref_value:
            perfdata.append(('predict_' + dsname, ref_value))
    else:
        perfdata = []

    return state, infotext, perfdata


def get_effective_service_level():
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
    """Works like time.mktime() but assumes the time_struct to be in UTC,
    not in local time."""
    import calendar
    return calendar.timegm(time_struct)


def passwordstore_get_cmdline(fmt, pw):
    """Use this to prepare a command line argument for using a password from the
    Check_MK password store or an explicitly configured password."""
    if not isinstance(pw, tuple):
        pw = ("password", pw)

    if pw[0] == "password":
        return fmt % pw[1]

    return ("store", pw[1], fmt)


def get_http_proxy(http_proxy):
    """Returns proxy URL to be used for HTTP requests

    Pass a value configured by the user using the HTTPProxyReference valuespec to this function
    and you will get back ether a proxy URL, an empty string to enforce no proxy usage or None
    to use the proxy configuration from the process environment.
    """
    return _config.get_http_proxy(http_proxy)


def get_agent_data_time():
    """Use this function to get the age of the agent data cache file
    of tcp or snmp hosts or None in case of piggyback data because
    we do not exactly know the latest agent data. Maybe one time
    we can handle this. For cluster hosts an exception is raised."""
    return _agent_cache_file_age(host_name(), check_type())


def _agent_cache_file_age(hostname, check_plugin_name):
    host_config = _config.get_config_cache().get_host_config(hostname)
    if host_config.is_cluster:
        raise MKGeneralException("get_agent_data_time() not valid for cluster")

    import cmk_base.check_utils
    if cmk_base.check_utils.is_snmp_check(check_plugin_name):
        cachefile = _paths.tcp_cache_dir + "/" + hostname + "." + check_plugin_name.split(".")[0]
    elif cmk_base.check_utils.is_tcp_check(check_plugin_name):
        cachefile = _paths.tcp_cache_dir + "/" + hostname
    else:
        cachefile = None

    if cachefile is not None and os.path.exists(cachefile):
        return _utils.cachefile_age(cachefile)

    return None


def get_parsed_item_data(check_function):
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
    cmk_base returning 3 (UNKN state) with an item not found message
    (see cmk_base/checking.py).
    """
    @functools.wraps(check_function)
    def wrapped_check_function(item, params, parsed):
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
    # type: (Callable) -> Callable
    """Validate function argument is a callable and return it"""

    if callable(filter_function):
        return filter_function
    elif filter_function is not None:
        raise ValueError("Filtering function is not a callable,"
                         " a {} has been given.".format(type(filter_function)))
    return lambda *entry: entry[0]


def discover(selector=None, default_params=None):
    # type (Callable, Union[dict, str]) -> Callable
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
    def roller(parsed):
        if isinstance(parsed, dict):
            return parsed.iteritems()
        elif isinstance(parsed, (list, tuple)):
            return parsed
        raise ValueError("Discovery function only works with dictionaries,"
                         " lists, and tuples you gave a {}".format(type(parsed)))

    def _discovery(filter_function):
        # type (Callable) -> Callable
        @functools.wraps(filter_function)
        def discoverer(parsed):
            # type (Union[dict,list]) -> Iterable[Tuple]

            params = default_params if isinstance(default_params, six.string_types +
                                                  (dict,)) else {}
            filterer = validate_filter(filter_function)
            from_dict = isinstance(parsed, dict)

            for entry in roller(parsed):
                if from_dict:
                    key, value = entry
                    name = filterer(key, value)
                else:
                    name = filterer(entry)

                if isinstance(name, six.string_types):
                    yield (name, params)
                elif name is True and from_dict:
                    yield (key, params)
                elif name is True and not from_dict:
                    yield (entry[0], params)
                elif name and hasattr(name, '__iter__'):
                    for new_name in name:
                        yield (new_name, params)

        return discoverer

    if callable(selector):
        return _discovery(selector)

    if selector is None and default_params is None:
        return _discovery(lambda *args: args[0])

    return _discovery


# NOTE: Currently this is not really needed, it is just here to keep any start
# import in sync with our intended API.
# TODO: Do we really need this? Is there code which uses a star import for this
# module?
__all__ = get_check_api_context().keys()
