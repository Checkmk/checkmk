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

import cmk.debug as _debug
from cmk.exceptions import MKGeneralException

# These imports are not meant for use in the API. So we prefix the names
# with an underscore. These names will be skipped when loading into the
# check context.
import cmk_base.utils as _utils
import cmk_base.console as _console
import cmk_base.config as _config
import cmk_base.rulesets as _rulesets
import cmk.defines as _defines
import cmk_base.snmp as _snmp
import cmk_base.item_state as _item_state
import cmk_base.prediction as _prediction

def get_check_context():
    return [ (k, v) for k, v in globals().items() if k[0] != "_" ]

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

# TODO: Move imports directly to checks?
import fnmatch
import math
import re
import socket
import sys
import time

from cmk.regex import regex
import cmk.render as render

# Names of texts usually output by checks
core_state_names = _defines.short_service_state_names()

# Symbolic representations of states in plugin output
state_markers = ["", "(!)", "(!!)", "(?)"]

BINARY     = _snmp.BINARY
CACHED_OID = _snmp.CACHED_OID

OID_END              = _snmp.OID_END
OID_STRING           = _snmp.OID_STRING
OID_BIN              = _snmp.OID_BIN
OID_END_BIN          = _snmp.OID_END_BIN
OID_END_OCTET_STRING = _snmp.OID_END_OCTET_STRING
binstring_to_int     = _snmp.binstring_to_int

# Is set before check execution
g_hostname            = "unknown" # Host currently being checked
g_service_description = None

def saveint(i):
    try:
        return int(i)
    except:
        return 0


def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0


# The function no_discovery_possible is as stub function used for
# those checks that do not support inventory. It must be known before
# we read in all the checks
def no_discovery_possible(check_type, info):
    _console.verbose("%s does not support discovery. Skipping it.\n", check_type)
    return []

service_extra_conf       = _rulesets.service_extra_conf
host_extra_conf          = _rulesets.host_extra_conf
in_binary_hostlist       = _rulesets.in_binary_hostlist
in_extraconf_hostlist    = _rulesets.in_extraconf_hostlist
hosttags_match_taglist   = _rulesets.hosttags_match_taglist
host_extra_conf_merged   = _rulesets.host_extra_conf_merged
get_rule_options         = _rulesets.get_rule_options
all_matching_hosts       = _rulesets.all_matching_hosts

checkgroup_parameters    = _config.checkgroup_parameters
tags_of_host             = _config.tags_of_host
nagios_illegal_chars     = _config.nagios_illegal_chars
is_ipv6_primary          = _config.is_ipv6_primary
is_cmc                   = _config.is_cmc

get_age_human_readable   = render.approx_age
get_bytes_human_readable = render.bytes
quote_shell_string       = _utils.quote_shell_string


# Similar to get_bytes_human_readable, but optimized for file
# sizes. Really only use this for files. We assume that for smaller
# files one wants to compare the exact bytes of a file, so the
# threshold to show the value as MB/GB is higher as the one of
# get_bytes_human_readable().
# TODO: Replace by some render.* function / move to render module?
def get_filesize_human_readable(size):
    if size < 4 * 1024 * 1024:
        return "%d B" % int(size)
    elif size < 4 * 1024 * 1024 * 1024:
        return "%.2f MB" % (float(size) / (1024 * 1024))
    else:
        return "%.2f GB" % (float(size) / (1024 * 1024 * 1024))


# TODO: Replace by some render.* function / move to render module?
def get_nic_speed_human_readable(speed):
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
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    else:
        return "never"


# TODO: Replace by some render.* function / move to render module?
def get_relative_date_human_readable(timestamp):
    now = time.time()
    if timestamp > now:
        return "in " + get_age_human_readable(timestamp - now)
    else:
        return get_age_human_readable(now - timestamp) + " ago"


# Format perc (0 <= perc <= 100 + x) so that precision
# digits are being displayed. This avoids a "0.00%" for
# very small numbers
# TODO: Replace by some render.* function / move to render module?
def get_percent_human_readable(perc, precision=2):
    if perc > 0:
        perc_precision = max(1, 2 - int(round(math.log(perc, 10))))
    else:
        perc_precision = 1
    return "%%.%df%%%%" % perc_precision % perc


#
# Counter handling
#

set_item_state                 = _item_state.set_item_state
get_item_state                 = _item_state.get_item_state
get_all_item_states            = _item_state.get_all_item_states
clear_item_state               = _item_state.clear_item_state
clear_item_states_by_full_keys = _item_state.clear_item_states_by_full_keys
get_rate                       = _item_state.get_rate
get_average                    = _item_state.get_average
# TODO: Cleanup checks and deprecate this
last_counter_wrap              = _item_state.last_counter_wrap

SKIP  = _item_state.SKIP
RAISE = _item_state.RAISE
ZERO  = _item_state.ZERO

MKCounterWrapped = _item_state.MKCounterWrapped

def check_levels(value, dsname, params, unit="", factor=1.0, scale=1.0, statemarkers=False):
    """Generic function for checking a value against levels

    This also supports predictive levels.

    value:   currently measured value
    dsname:  name of the datasource in the RRD that corresponds to this value
    unit:    unit to be displayed in the plugin output, e.g. "MB/s"
    factor:  the levels are multiplied with this factor before applying
             them to the value. This is being used for the CPU load check
             currently. The levels here are "per CPU", so the number of
             CPUs is used as factor.
    scale:   Scale of the levels in relation to "value" and the value in the RRDs.
             For example if the levels are specified in GB and the RRD store KB, then
             the scale is 1024*1024.
    """
    if unit:
        unit = " " + unit # Insert space before MB, GB, etc.
    perfdata = []
    infotexts = []

    def scale_value(v):
        if v == None:
            return None
        else:
            return v * factor * scale

    def levelsinfo_ty(ty, warn, crit, unit):
        return ("warn/crit %s %.2f/%.2f %s" % (ty, warn, crit, unit)).strip()

    # None or (None, None) -> do not check any levels
    if params == None or params == (None, None):
        return 0, "", []

    # Pair of numbers -> static levels
    elif type(params) == tuple:
        if len(params) == 2: # upper warn and crit
            warn_upper, crit_upper = scale_value(params[0]), scale_value(params[1])
            warn_lower, crit_lower = None, None

        else: # upper and lower warn and crit
            warn_upper, crit_upper = scale_value(params[0]), scale_value(params[1])
            warn_lower, crit_lower = scale_value(params[2]), scale_value(params[3])

        ref_value = None

    # Dictionary -> predictive levels
    else:
        try:
            ref_value, ((warn_upper, crit_upper), (warn_lower, crit_lower)) = \
                      _prediction.get_levels(g_hostname, g_service_description,
                                dsname, params, "MAX", levels_factor=factor * scale)

            if ref_value:
                infotexts.append("predicted reference: %.2f%s" % (ref_value / scale, unit))
            else:
                infotexts.append("no reference for prediction yet")

        except MKGeneralException, e:
            ref_value = None
            warn_upper, crit_upper, warn_lower, crit_lower = None, None, None, None
            infotexts.append("no reference for prediction (%s)" % e)

        except Exception, e:
            if _debug.enabled():
                raise
            return 3, "%s" % e, []

    if ref_value:
        perfdata.append(('predict_' + dsname, ref_value))

    # Critical cases
    if crit_upper != None and value >= crit_upper:
        state = 2
        infotexts.append(levelsinfo_ty("at", warn_upper / scale, crit_upper / scale, unit))
    elif crit_lower != None and value < crit_lower:
        state = 2
        infotexts.append(levelsinfo_ty("below", warn_lower / scale, crit_lower / scale, unit))

    # Warning cases
    elif warn_upper != None and value >= warn_upper:
        state = 1
        infotexts.append(levelsinfo_ty("at", warn_upper / scale, crit_upper / scale, unit))
    elif warn_lower != None and value < warn_lower:
        state = 1
        infotexts.append(levelsinfo_ty("below", warn_lower / scale, crit_lower / scale, unit))

    # OK
    else:
        state = 0

    if infotexts:
        infotext = " (" + ", ".join(infotexts) + ")"
    else:
        infotext = ""

    if state and statemarkers:
        if state == 1:
            infotext += "(!)"
        else:
            infotext += "(!!)"

    return state, infotext, perfdata


# retrive the service level that applies to the calling check.
def get_effective_service_level():
    service_levels = _rulesets.service_extra_conf(g_hostname, g_service_description,
                                        _config.service_service_levels)

    if service_levels:
        return service_levels[0]
    else:
        service_levels = _rulesets.host_extra_conf(g_hostname, _config.host_service_levels)
        if service_levels:
            return service_levels[0]
    return 0


# like time.mktime but assumes the time_struct to be in utc, not in local time.
def utc_mktime(time_struct):
    import calendar
    return calendar.timegm(time_struct)


def passwordstore_get_cmdline(fmt, pw):
    if type(pw) != tuple:
        pw = ("password", pw)

    if pw[0] == "password":
        return fmt % pw[1]
    else:
        return ("store", pw[1], fmt)


# Use this function to get the age of the agent data cache file
# of tcp or snmp hosts or None in case of piggyback data because
# we do not exactly know the latest agent data. Maybe one time
# we can handle this. For cluster hosts an exception is raised.
def get_agent_data_time():
    return _agent_cache_file_age(g_hostname, g_check_type)


def _agent_cache_file_age(hostname, check_type):
    if _config.is_cluster(hostname):
        raise MKGeneralException("get_agent_data_time() not valid for cluster")

    import cmk_base.checks as checks
    if checks.is_snmp_check(check_type):
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname + "." + check_type.split(".")[0]
    elif checks.is_tcp_check(check_type):
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname
    else:
        cachefile = None

    if cachefile is not None and os.path.exists(cachefile):
        return _utils.cachefile_age(cachefile)
    else:
        return None
