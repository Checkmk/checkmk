#!/usr/bin/python
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

#   .--Imports-------------------------------------------------------------.
#   |               ___                            _                       |
#   |              |_ _|_ __ ___  _ __   ___  _ __| |_ ___                 |
#   |               | || '_ ` _ \| '_ \ / _ \| '__| __/ __|                |
#   |               | || | | | | | |_) | (_) | |  | |_\__ \                |
#   |              |___|_| |_| |_| .__/ \___/|_|   \__|___/                |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   |  Import other Python modules                                         |
#   '----------------------------------------------------------------------'

import sys

# Remove precompiled directory from sys.path. Leaving it in the path
# makes problems when host names (name of precompiled files) are equal
# to python module names like "random"
sys.path.pop(0)

import socket
import os
import fnmatch
import time
import re
import signal
import math
import tempfile
import traceback
import subprocess

from cmk.exceptions import MKGeneralException, MKTerminate
from cmk.regex import regex
import cmk.tty as tty
import cmk.render as render
import cmk.crash_reporting as crash_reporting
import cmk.cpu_tracking as cpu_tracking
import cmk.paths

import cmk_base.agent_simulator
import cmk_base.utils
import cmk_base.prediction
import cmk_base.console as console
import cmk_base

# PLANNED CLEANUP:
# - central functions for outputting verbose information and bailing
#   out because of errors. Remove all explicit "if cmk.debug.enabled()...".
#   Note: these new functions should force a flush() if TTY is not
#   a terminal (so that error messages arrive the CMC in time)
# - --debug should *only* influence exception handling
# - introduce second levels of verbosity, that takes over debug output
#   from --debug
# - remove all remaining print commands and use sys.stdout.write instead
#   or define a new output function

#.
#   .--Globals-------------------------------------------------------------.
#   |                    ____ _       _           _                        |
#   |                   / ___| | ___ | |__   __ _| |___                    |
#   |                  | |  _| |/ _ \| '_ \ / _` | / __|                   |
#   |                  | |_| | | (_) | |_) | (_| | \__ \                   |
#   |                   \____|_|\___/|_.__/ \__,_|_|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of global variables and constants.                       |
#   '----------------------------------------------------------------------'

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
g_infocache                  = {} # In-memory cache of host info.
g_agent_cache_info           = {} # Information about agent caching
g_agent_already_contacted    = {} # do we have agent data from this host?
g_item_state                 = {} # storing counters of one host
g_hostname                   = "unknown" # Host currently being checked
g_aggregated_service_results = {}   # store results for later submission
g_inactive_timerperiods      = None # Cache for current state of timeperiods
g_last_counter_wrap          = None
nagios_command_pipe          = None # Filedescriptor to open nagios command pipe.
checkresult_file_fd          = None
checkresult_file_path        = None
g_single_oid_hostname        = None
g_single_oid_cache           = {}
g_broken_snmp_hosts          = set([])
g_broken_agent_hosts         = set([])
g_timeout                    = None

# variables set later by getopt. These are defined here since in precompiled
# mode the module check_mk.py is not present and we need all options to be
# present.
opt_dont_submit              = False
opt_showplain                = False
opt_showperfdata             = False
opt_use_cachefile            = False
opt_no_tcp                   = False
opt_no_cache                 = False
opt_no_snmp_hosts            = False
opt_use_snmp_walk            = False
opt_cleanup_autochecks       = False
opt_keepalive                = False
opt_cmc_relfilename          = "config"
opt_keepalive_fd             = None
opt_oids                     = []
opt_extra_oids               = []
opt_force                    = False
fake_dns                     = False

# Names of texts usually output by checks
core_state_names = ["OK", "WARN", "CRIT", "UNKNOWN"]

# Symbolic representations of states in plugin output
state_markers = ["", "(!)", "(!!)", "(?)"]

# Constants for counters
SKIP  = None
RAISE = False
ZERO  = 0.0


class MKCounterWrapped(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKCounterWrapped, self).__init__(reason)
    def __str__(self):
        return self.reason

class MKAgentError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKAgentError, self).__init__(reason)
    def __str__(self):
        return self.reason

class MKParseFunctionError(Exception):
    def __init__(self, exception_type, exception, backtrace):
        self.exception_type = exception_type
        self.exception = exception
        self.backtrace = backtrace
        super(MKParseFunctionError, self).__init__(self, exception_type, exception, backtrace)

    def exc_info(self):
        return self.exception_type, self.exception, self.backtrace

    def __str__(self):
        return "%s\n%s" % (self.exception, self.backtrace)

class MKSNMPError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKSNMPError, self).__init__(reason)
    def __str__(self):
        return self.reason

class MKSkipCheck(Exception):
    pass

# This exception is raised when a previously configured timeout is reached.
# It is used during keepalive mode. It is also used by the automations
# which have a timeout set.
class MKTimeout(Exception):
    pass


#.
#   .--Get data------------------------------------------------------------.
#   |                 ____      _         _       _                        |
#   |                / ___| ___| |_    __| | __ _| |_ __ _                 |
#   |               | |  _ / _ \ __|  / _` |/ _` | __/ _` |                |
#   |               | |_| |  __/ |_  | (_| | (_| | || (_| |                |
#   |                \____|\___|\__|  \__,_|\__,_|\__\__,_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions for getting monitoring data from TCP/SNMP agent.          |
#   '----------------------------------------------------------------------'

def apply_parse_function(info, section_name):
    # Now some check types define a parse function. In that case the
    # info is automatically being parsed by that function - on the fly.
    if info != None and section_name in check_info:
        parse_function = check_info[section_name]["parse_function"]
        if parse_function:
            try:
                # Prepare unique context for get_rate() and get_average()
                global g_check_type, g_checked_item
                g_check_type = section_name
                g_checked_item = None
                return parse_function(info)
            except Exception:
                if cmk.debug.enabled():
                    raise

                # In case of a failed parse function return the exception instead of
                # an empty result.
                raise MKParseFunctionError(*sys.exc_info())

    return info

def get_info_for_check(hostname, ipaddress, section_name, max_cachefile_age=None, ignore_check_interval=False):
    info = apply_parse_function(get_host_info(hostname, ipaddress, section_name, max_cachefile_age, ignore_check_interval), section_name)
    if info != None and section_name in check_info and check_info[section_name]["extra_sections"]:
        info = [ info ]
        for es in check_info[section_name]["extra_sections"]:
            try:
                info.append(apply_parse_function(get_host_info(hostname, ipaddress, es, max_cachefile_age, ignore_check_interval=False), es))
            except:
                info.append(None)
    return info


# This is the main function for getting information needed by a
# certain check. It is called once for each check type. For SNMP this
# is needed since not all data for all checks is fetched at once. For
# TCP based checks the first call to this function stores the
# retrieved data in a global variable. Later calls to this function
# get their data from there.

# If the host is a cluster, the information is fetched from all its
# nodes an then merged per-check-wise.

# For cluster checks the monitoring core does not provide the IP addresses
# of the node.  We need to do DNS-lookups in that case :-(. We could avoid
# that at least in case of precompiled checks. On the other hand, cluster
# checks usually use existing cache files, if check_mk is not misconfigured,
# and thus do no network activity at all...


def add_nodeinfo(info, nodename):
    new_info = []
    for line in info:
        if len(line) > 0 and type(line[0]) == list:
            new_entry = []
            for entry in line:
                new_entry.append([ nodename ] + entry)
            new_info.append(new_entry)
        else:
            new_info.append([ nodename ] + line)
    return new_info


def get_host_info(hostname, ipaddress, checkname, max_cachefile_age=None, ignore_check_interval=False):
    # If the check want's the node info, we add an additional
    # column (as the first column) with the name of the node
    # or None (in case of non-clustered nodes). On problem arises,
    # if we deal with subchecks. We assume that all subchecks
    # have the same setting here. If not, let's raise an exception.
    has_nodeinfo = check_info.get(checkname, {}).get("node_info", False)

    nodes = nodes_of(hostname)
    if nodes != None:
        info = []
        at_least_one_without_exception = False
        exception_texts = []
        set_use_cachefile()
        is_snmp_error = False
        for node in nodes:
            # If an error with the agent occurs, we still can (and must)
            # try the other nodes.
            try:
                # We must ignore the SNMP check interval when dealing with SNMP
                # checks on cluster nodes because the cluster is always reading
                # the cache files of the nodes.
                ipaddress = lookup_ip_address(node)
                new_info = get_realhost_info(node, ipaddress, checkname,
                               max_cachefile_age == None and cluster_max_cachefile_age or max_cachefile_age,
                               ignore_check_interval=True)
                if new_info != None:
                    if has_nodeinfo:
                        new_info = add_nodeinfo(new_info, node)

                    info += new_info
                    at_least_one_without_exception = True
            except MKSkipCheck:
                at_least_one_without_exception = True
            except MKAgentError, e:
                if str(e) != "": # only first error contains text
                    exception_texts.append(str(e))
                g_broken_agent_hosts.add(node)
            except MKSNMPError, e:
                if str(e) != "": # only first error contains text
                    exception_texts.append(str(e))
                g_broken_snmp_hosts.add(node)
                is_snmp_error = True
        if not at_least_one_without_exception:
            if is_snmp_error:
                raise MKSNMPError(", ".join(exception_texts))
            else:
                raise MKAgentError(", ".join(exception_texts))

    else:
        info = get_realhost_info(hostname, ipaddress, checkname,
                      max_cachefile_age == None and check_max_cachefile_age or max_cachefile_age,
                      ignore_check_interval)
        if info != None and has_nodeinfo:
            if clusters_of(hostname):
                add_host = hostname
            else:
                add_host = None
            info = add_nodeinfo(info, add_host)

    return info


# Gets info from a real host (not a cluster). There are three possible
# ways: TCP, SNMP and external command.  This function raises
# MKAgentError or MKSNMPError, if there could not retrieved any data. It returns [],
# if the agent could be contacted but the data is empty (no items of
# this check type).
#
# What makes the thing a bit tricky is the fact, that data
# might have to be fetched via SNMP *and* TCP for one host
# (even if this is unlikeyly)
#
# What makes the thing even more tricky is the new piggyback
# function, that allows one host's agent to send data for another
# host.
#
# This function assumes, that each check type is queried
# only once for each host.
def get_realhost_info(hostname, ipaddress, check_type, max_cache_age,
                      ignore_check_interval=False, use_snmpwalk_cache=True):

    info = get_cached_hostinfo(hostname)
    if info and info.has_key(check_type):
        return info[check_type]

    cache_relpath = hostname + "." + check_type

    # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
    # Please note, that if the check_type is foo.bar then we lookup the
    # snmp info for "foo", not for "foo.bar".
    info_type = check_type.split(".")[0]
    if info_type in snmp_info:
        oid_info = snmp_info[info_type]
    elif info_type in inv_info:
        oid_info = inv_info[info_type].get("snmp_info")
    else:
        oid_info = None

    if oid_info:
        cache_path = cmk.paths.tcp_cache_dir + "/" + cache_relpath

        # Handle SNMP check interval. The idea: An SNMP check should only be
        # executed every X seconds. Skip when called too often.
        check_interval = check_interval_of(hostname, check_type)
        if not ignore_check_interval \
           and not opt_dont_submit \
           and check_interval is not None and os.path.exists(cache_path) \
           and cachefile_age(cache_path) < check_interval * 60:
            # cache file is newer than check_interval, skip this check
            raise MKSkipCheck()

        try:
            content = read_cache_file(cache_relpath, max_cache_age)
        except:
            if simulation_mode and not opt_no_cache:
                return # Simply ignore missing SNMP cache files
            raise

        if content:
            return eval(content)
        # Not cached -> need to get info via SNMP

        # Try to contact host only once
        if hostname in g_broken_snmp_hosts:
            raise MKSNMPError("")

        # New in 1.1.3: oid_info can now be a list: Each element
        # of that list is interpreted as one real oid_info, fetches
        # a separate snmp table. The overall result is then the list
        # of these results.
        if type(oid_info) == list:
            table = [ get_snmp_table(hostname, ipaddress, check_type, entry, use_snmpwalk_cache) for entry in oid_info ]
            # if at least one query fails, we discard the hole table
            if None in table:
                table = None
        else:
            table = get_snmp_table(hostname, ipaddress, check_type, oid_info, use_snmpwalk_cache)

        store_cached_checkinfo(hostname, check_type, table)
        # only write cache file in non interactive mode. Otherwise it would
        # prevent the regular checking from getting status updates during
        # interactive debugging, for example with cmk -nv.
        if not opt_dont_submit:
            write_cache_file(cache_relpath, repr(table) + "\n")
        return table

    # Note: even von SNMP-tagged hosts TCP based checks can be used, if
    # the data comes piggyback!

    # No SNMP check. Then we must contact the check_mk_agent. Have we already
    # tried to get data from the agent? If yes we must not do that again! Even if
    # no cache file is present.
    if g_agent_already_contacted.has_key(hostname):
        raise MKAgentError("")

    g_agent_already_contacted[hostname] = True
    store_cached_hostinfo(hostname, []) # leave emtpy info in case of error

    # If we have piggyback data for that host from another host,
    # then we prepend this data and also tolerate a failing
    # normal Check_MK Agent access.
    piggy_output = get_piggyback_info(hostname) + get_piggyback_info(ipaddress)

    output = ""
    agent_failed_exc = None
    if is_tcp_host(hostname):
        try:
            output = get_agent_info(hostname, ipaddress, max_cache_age)
        except MKTimeout:
            raise

        except Exception, e:
            agent_failed_exc = e
            # Remove piggybacked information from the host (in the
            # role of the pig here). Why? We definitely haven't
            # reached that host so its data from the last time is
            # not valid any more.
            remove_piggyback_info_from(hostname)

            if not piggy_output:
                raise
            elif cmk.debug.enabled():
                raise

    output += piggy_output

    if len(output) == 0 and is_tcp_host(hostname):
        raise MKAgentError("Empty output from agent")
    elif len(output) == 0:
        return
    elif len(output) < 16:
        raise MKAgentError("Too short output from agent: '%s'" % output)

    info, piggybacked, persisted, agent_cache_info = parse_info(output.split("\n"), hostname)
    g_agent_cache_info.setdefault(hostname, {}).update(agent_cache_info)
    store_piggyback_info(hostname, piggybacked)
    store_persisted_info(hostname, persisted)
    store_cached_hostinfo(hostname, info)

    # Add information from previous persisted agent outputs, if those
    # sections are not available in the current output
    # TODO: In the persisted sections the agent_cache_info is missing
    add_persisted_info(hostname, info)

    # If the agent has failed and the information we seek is
    # not contained in the piggy data, raise an exception
    if check_type not in info:
        if agent_failed_exc:
            raise MKAgentError("Cannot get information from agent (%s), processing only piggyback data." % agent_failed_exc)
        else:
            return []

    return info[check_type] # return only data for specified check

def store_persisted_info(hostname, persisted):
    dirname = cmk.paths.var_dir + "/persisted/"
    if persisted:
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        file_path = "%s/%s" % (dirname, hostname)
        file("%s.#new" % file_path, "w").write("%r\n" % persisted)
        os.rename("%s.#new" % file_path, file_path)

        console.verbose("Persisted sections %s.\n" % ", ".join(persisted.keys()))


def add_persisted_info(hostname, info):
    file_path = cmk.paths.var_dir + "/persisted/" + hostname
    try:
        persisted = eval(file(file_path).read())
    except:
        return

    now = time.time()
    modified = False
    for section, entry in persisted.items():
        if len(entry) == 2:
            persisted_from = None
            persisted_until, persisted_section = entry
        else:
            persisted_from, persisted_until, persisted_section = entry
            g_agent_cache_info[hostname][section] = (persisted_from, persisted_until - persisted_from)

        if now < persisted_until or opt_force:
            if section not in info:
                info[section] = persisted_section
                console.vverbose("Added persisted section %s.\n" % section)
        else:
            console.verbose("Persisted section %s is outdated by %d seconds. Deleting it.\n" % (
                    section, now - persisted_until))
            del persisted[section]
            modified = True

    if not persisted:
        try:
            os.remove(file_path)
        except OSError:
            pass
    elif modified:
        store_persisted_info(hostname, persisted)


def get_piggyback_files(hostname):
    files = []
    dir = cmk.paths.tmp_dir + "/piggyback/" + hostname
    if os.path.exists(dir):
        for sourcehost in os.listdir(dir):
            if sourcehost not in ['.', '..'] \
               and not sourcehost.startswith(".new."):
                file_path = dir + "/" + sourcehost

                if cachefile_age(file_path) > piggyback_max_cachefile_age:
                    console.verbose("Piggyback file %s is outdated by %d seconds. Deleting it.\n" %
                        (file_path, cachefile_age(file_path) - piggyback_max_cachefile_age))
                    os.remove(file_path)
                    continue

                files.append((sourcehost, file_path))
    return files


def has_piggyback_info(hostname):
    return get_piggyback_files(hostname) != []


def get_piggyback_info(hostname):
    output = ""
    if not hostname:
        return output
    for sourcehost, file_path in get_piggyback_files(hostname):
        console.verbose("Using piggyback information from host %s.\n" % sourcehost)
        output += file(file_path).read()
    return output


def store_piggyback_info(sourcehost, piggybacked):
    piggyback_path = cmk.paths.tmp_dir + "/piggyback/"
    for backedhost, lines in piggybacked.items():
        console.verbose("Storing piggyback data for %s.\n" % backedhost)
        dir = piggyback_path + backedhost
        if not os.path.exists(dir):
            os.makedirs(dir)
        out = file(dir + "/.new." + sourcehost, "w")
        for line in lines:
            out.write("%s\n" % line)
        os.rename(dir + "/.new." + sourcehost, dir + "/" + sourcehost)

    # Remove piggybacked information that is not
    # being sent this turn
    remove_piggyback_info_from(sourcehost, keep=piggybacked.keys())


def remove_piggyback_info_from(sourcehost, keep=None):
    if keep is None:
        keep = []

    removed = 0
    piggyback_path = cmk.paths.tmp_dir + "/piggyback/"
    if not os.path.exists(piggyback_path):
        return # Nothing to do

    for backedhost in os.listdir(piggyback_path):
        if backedhost not in ['.', '..'] and backedhost not in keep:
            path = piggyback_path + backedhost + "/" + sourcehost
            if os.path.exists(path):
                console.verbose("Removing stale piggyback file %s\n" % path)
                os.remove(path)
                removed += 1

            # Remove directory if empty
            try:
                os.rmdir(piggyback_path + backedhost)
            except:
                pass
    return removed


def translate_piggyback_host(sourcehost, backedhost):
    translation = get_piggyback_translation(sourcehost)
    return do_hostname_translation(translation, backedhost)


# When changing this keep it in sync with
# a) check_mk_base.py: do_hostname_translation()
# b) wato.py:          do_hostname_translation()
# FIXME TODO: Move the common do_hostname_translation() in a central Check_MK module
def do_hostname_translation(translation, hostname):
    # 1. Case conversion
    caseconf = translation.get("case")
    if caseconf == "upper":
        hostname = hostname.upper()
    elif caseconf == "lower":
        hostname = hostname.lower()

    # 2. Drop domain part (not applied to IP addresses!)
    if translation.get("drop_domain") and not hostname[0].isdigit():
        hostname = hostname.split(".", 1)[0]

    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    hostname = decode_incoming_string(hostname)

    # 3. Multiple regular expression conversion
    if type(translation.get("regex")) == tuple:
        translations = [translation.get("regex")]
    else:
        translations = translation.get("regex", [])

    for expr, subst in translations:
        if not expr.endswith('$'):
            expr += '$'
        rcomp = regex(expr)
        # re.RegexObject.sub() by hand to handle non-existing references
        mo = rcomp.match(hostname)
        if mo:
            hostname = subst
            for nr, text in enumerate(mo.groups("")):
                hostname = hostname.replace("\\%d" % (nr+1), text)
            break

    # 4. Explicity mapping
    for from_host, to_host in translation.get("mapping", []):
        if from_host == hostname:
            hostname = to_host
            break

    return hostname.encode('utf-8') # change back to UTF-8 encoded string


def read_cache_file(relpath, max_cache_age):
    # Cache file present, caching allowed? -> read from cache
    cachefile = cmk.paths.tcp_cache_dir + "/" + relpath
    if os.path.exists(cachefile) and (
        (opt_use_cachefile and ( not opt_no_cache ) )
        or (simulation_mode and not opt_no_cache) ):
        if cachefile_age(cachefile) <= max_cache_age or simulation_mode:
            f = open(cachefile, "r")
            result = f.read(10000000)
            f.close()
            if len(result) > 0:
                console.verbose("Using data from cachefile %s.\n" % cachefile)
                return result
        else:
            console.vverbose("Skipping cache file %s: Too old "
                             "(age is %d sec, allowed is %s sec)\n" %
                   (cachefile, cachefile_age(cachefile), max_cache_age))

    if simulation_mode and not opt_no_cache:
        raise MKAgentError("Simulation mode and no cachefile present.")

    if opt_no_tcp:
        raise MKAgentError("Host is unreachable, no usable cache file present")


def write_cache_file(relpath, output):
    cachefile = cmk.paths.tcp_cache_dir + "/" + relpath
    if not os.path.exists(cmk.paths.tcp_cache_dir):
        try:
            os.makedirs(cmk.paths.tcp_cache_dir)
        except Exception, e:
            raise MKGeneralException("Cannot create directory %s: %s" % (cmk.paths.tcp_cache_dir, e))
    try:
        # write retrieved information to cache file - if we are not root.
        # We assume that the core never runs as root.
        if not i_am_root():
            f = open(cachefile, "w+")
            f.write(output)
            f.close()
    except Exception, e:
        raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))


# Get information about a real host (not a cluster node) via TCP
# or by executing an external program. ipaddress may be None.
# In that case it will be looked up if needed. Also caching will
# be handled here
def get_agent_info(hostname, ipaddress, max_cache_age):
    if ipaddress in [ "0.0.0.0", "::" ]:
        raise MKAgentError("Failed to lookup IP address and no explicit IP address configured")

    output = read_cache_file(hostname, max_cache_age)
    if not output:
        # Try to contact every host only once
        if hostname in g_broken_agent_hosts:
            raise MKAgentError("")

        # If the host is listed in datasource_programs the data from
        # that host is retrieved by calling an external program (such
        # as ssh or rsh or agent_vsphere) instead of a TCP connect.
        commandline = get_datasource_program(hostname, ipaddress)
        if commandline:
            cpu_tracking.push_phase("ds")
            output = get_agent_info_program(commandline)
        else:
            cpu_tracking.push_phase("agent")
            output = get_agent_info_tcp(hostname, ipaddress)
        cpu_tracking.pop_phase()

        # Got new data? Write to cache file
        write_cache_file(hostname, output)

    if agent_simulator:
        output = cmk_base.agent_simulator.process(output)

    return output

# Get data in case of external program
def get_agent_info_program(commandline):
    exepath = commandline.split()[0] # for error message, hide options!

    console.vverbose("Calling external program %s\n" % commandline)
    p = None
    try:
        if monitoring_core == "cmc":
            p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull),
                                 stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                 preexec_fn=os.setsid, close_fds=True)
        else:
            # We can not create a separate process group when running Nagios
            # Upon reaching the service_check_timeout Nagios only kills the process
            # group of the active check.
            p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull),
                                 stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                 close_fds=True)
        stdout, stderr = p.communicate()
        exitstatus = p.returncode
    except MKTimeout:
        # On timeout exception try to stop the process to prevent child process "leakage"
        if p:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        raise
    except Exception, e:
        raise MKAgentError("Could not execute '%s': %s" % (exepath, e))
    finally:
        # The stdout and stderr pipe are not closed correctly on a MKTimeout
        # Normally these pipes getting closed after p.communicate finishes
        # Closing them a second time in a OK scenario won't hurt neither..
        if p:
            p.stdout.close()
            p.stderr.close()

    if exitstatus:
        if exitstatus == 127:
            raise MKAgentError("Program '%s' not found (exit code 127)" % exepath)
        else:
            raise MKAgentError("Agent exited with code %d: %s" % (exitstatus, stderr))
    return stdout


def decrypt_package(encrypted_pkg, encryption_key):
    from Crypto.Cipher import AES
    from hashlib import md5

    unpad = lambda s : s[0:-ord(s[-1])]

    # Adapt OpenSSL handling of key and iv
    def derive_key_and_iv(password, key_length, iv_length):
        d = d_i = ''
        while len(d) < key_length + iv_length:
            d_i = md5(d_i + password).digest()
            d += d_i
        return d[:key_length], d[key_length:key_length+iv_length]

    key, iv = derive_key_and_iv(encryption_key, 32, AES.block_size)
    decryption_suite = AES.new(key, AES.MODE_CBC, iv)
    decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)

    # Strip of fill bytes of openssl
    return unpad(decrypted_pkg)


# Get data in case of TCP
def get_agent_info_tcp(hostname, ipaddress, port = None):
    if not ipaddress:
        raise MKGeneralException("Cannot contact agent: host '%s' has no IP address." % hostname)

    if port is None:
        port = agent_port_of(hostname)

    encryption_settings = agent_encryption_settings(hostname)

    try:
        s = socket.socket(is_ipv6_primary(hostname) and socket.AF_INET6 or socket.AF_INET,
                          socket.SOCK_STREAM)
        try:
            s.settimeout(tcp_connect_timeout)
        except:
            pass # some old Python versions lack settimeout(). Better ignore than fail
        console.vverbose("Connecting via TCP to %s:%d.\n" % (ipaddress, port))
        s.connect((ipaddress, port))
        # Immediately close sending direction. We do not send any data
        # s.shutdown(socket.SHUT_WR)
        try:
            s.setblocking(1)
        except:
            pass
        output = ""
        try:
            while True:
                out = s.recv(4096, socket.MSG_WAITALL)
                if out and len(out) > 0:
                    output += out
                else:
                    break
        except Exception, e:
            # Python seems to skip closing the socket under certain
            # conditions, leaving open filedescriptors and sockets in
            # CLOSE_WAIT. This happens one a timeout (ALERT signal)
            s.close()
            raise

        s.close()
        if len(output) == 0: # may be caused by xinetd not allowing our address
            raise MKAgentError("Empty output from agent at TCP port %d" % port)

        if encryption_settings["use_regular"] == "enforce" and \
            output.startswith("<<<check_mk>>>"):
            raise MKGeneralException("Agent output is plaintext but encryption is enforced by configuration")

        if encryption_settings["use_regular"] != "disabled":
            try:
                # currently ignoring version and timestamp
                #protocol_version = int(output[0:2])

                output = decrypt_package(output[2:], encryption_settings["passphrase"])
            except Exception, e:
                if encryption_settings["use_regular"] == "enforce":
                    raise MKGeneralException("Failed to decrypt agent output: %s" % e)
                else:
                    # of course the package might indeed have been encrypted but
                    # in an incorrect format, but how would we find that out?
                    # In this case processing the output will fail
                    pass

        return output
    except MKAgentError, e:
        raise
    except MKTimeout:
        raise
    except Exception, e:
        raise MKAgentError("Cannot get data from TCP port %s:%d: %s" %
                           (ipaddress, port, e))


# Gets all information about one host so far cached.
# Returns None if nothing has been stored so far
def get_cached_hostinfo(hostname):
    return g_infocache.get(hostname, None)

# store complete information about a host
def store_cached_hostinfo(hostname, info):
    oldinfo = get_cached_hostinfo(hostname)
    if oldinfo:
        oldinfo.update(info)
        g_infocache[hostname] = oldinfo
    else:
        g_infocache[hostname] = info

# store information about one check type
def store_cached_checkinfo(hostname, checkname, table):
    info = get_cached_hostinfo(hostname)
    if info:
        info[checkname] = table
    else:
        g_infocache[hostname] = { checkname: table }


# Split agent output in chunks, splits lines by whitespaces.
# Returns a tuple of:
# 1. A dictionary from "sectionname" to a list of rows
# 2. piggy-backed data for other hosts
# 3. Sections to be persisted for later usage
# 4. Agent cache information (dict section name -> (cached_at, cache_interval))
def parse_info(lines, hostname):
    info = {}
    piggybacked = {} # unparsed info for other hosts
    persist = {} # handle sections with option persist(...)
    host = None
    section = []
    section_options = {}
    agent_cache_info = {}
    separator = None
    encoding  = None
    for line in lines:
        line = line.rstrip("\r")
        stripped_line = line.strip()
        if stripped_line[:4] == '<<<<' and stripped_line[-4:] == '>>>>':
            host = stripped_line[4:-4]
            if not host:
                host = None
            else:
                host = translate_piggyback_host(hostname, host)
                if host == hostname:
                    host = None # unpiggybacked "normal" host

                # Protect Check_MK against unallowed host names. Normally source scripts
                # like agent plugins should care about cleaning their provided host names
                # up, but we need to be sure here to prevent bugs in Check_MK code.
                # a) Replace spaces by underscores
                if host:
                    host = host.replace(" ", "_")

        elif host: # processing data for an other host
            piggybacked.setdefault(host, []).append(line)

        # Found normal section header
        # section header has format <<<name:opt1(args):opt2:opt3(args)>>>
        elif stripped_line[:3] == '<<<' and stripped_line[-3:] == '>>>':
            section_header = stripped_line[3:-3]
            headerparts = section_header.split(":")
            section_name = headerparts[0]
            section_options = {}
            for o in headerparts[1:]:
                opt_parts = o.split("(")
                opt_name = opt_parts[0]
                if len(opt_parts) > 1:
                    opt_args = opt_parts[1][:-1]
                else:
                    opt_args = None
                section_options[opt_name] = opt_args

            section = info.get(section_name, None)
            if section == None: # section appears in output for the first time
                section = []
                info[section_name] = section
            try:
                separator = chr(int(section_options["sep"]))
            except:
                separator = None

            # Split of persisted section for server-side caching
            if "persist" in section_options:
                until = int(section_options["persist"])
                cached_at = int(time.time()) # Estimate age of the data
                cache_interval = int(until - cached_at)
                agent_cache_info[section_name] = (cached_at, cache_interval)
                persist[section_name] = ( cached_at, until, section )

            if "cached" in section_options:
                agent_cache_info[section_name] = tuple(map(int, section_options["cached"].split(",")))

            # The section data might have a different encoding
            encoding = section_options.get("encoding")

        elif stripped_line != '':
            if "nostrip" not in section_options:
                line = stripped_line

            if encoding:
                line = decode_incoming_string(line, encoding)
            else:
                line = decode_incoming_string(line)

            section.append(line.split(separator))

    return info, piggybacked, persist, agent_cache_info


def decode_incoming_string(s, encoding="utf-8"):
    try:
        return s.decode(encoding)
    except:
        return s.decode(fallback_agent_output_encoding)


def cachefile_age(filename):
    try:
        return time.time() - os.stat(filename)[8]
    except Exception, e:
        raise MKGeneralException("Cannot determine age of cache file %s: %s" \
                                 % (filename, e))

#.
#   .--Item state and counters---------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|___  _   _ _ __ | |_ ___ _ __ ___                |
#   |              | |   / _ \| | | | '_ \| __/ _ \ '__/ __|               |
#   |              | |__| (_) | |_| | | | | ||  __/ |  \__ \               |
#   |               \____\___/ \__,_|_| |_|\__\___|_|  |___/               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  These functions allow checks to keep a memory until the next time   |
#   |  the check is being executed. The most frequent use case is compu-   |
#   |  tation of rates from two succeeding counter values. This is done    |
#   |  via the helper function get_rate(). Averaging is another example    |
#   |  and done by get_average().                                          |
#   |                                                                      |
#   |  While a host is being checked this memory is kept in g_item_state.  |
#   |  That is a dictionary. The keys are unique to one check type and     |
#   |  item. The value is free form.                                       |
#   |                                                                      |
#   |  Note: The item state is kept in tmpfs and not reboot-persistant.    |
#   |  Do not store long-time things here. Also do not store complex       |
#   |  structures like log files or stuff.
#   '----------------------------------------------------------------------'


def load_item_state(hostname):
    global g_item_state
    filename = cmk.paths.counters_dir + "/" + hostname
    try:
        g_item_state = eval(file(filename).read())
    except:
        g_item_state = {}


def save_item_state(hostname):
    if not opt_dont_submit and not i_am_root(): # never writer counters as root
        filename = cmk.paths.counters_dir + "/" + hostname
        try:
            if not os.path.exists(cmk.paths.counters_dir):
                os.makedirs(cmk.paths.counters_dir)
            file(filename, "w").write("%r\n" % g_item_state)
        except Exception, e:
            raise MKGeneralException("Cannot write to %s: %s" % (filename, traceback.format_exc()))


# Store arbitrary values until the next execution of a check
def set_item_state(user_key, state):
    g_item_state[unique_item_state_key(user_key)] = state


def get_item_state(user_key, default=None):
    return g_item_state.get(unique_item_state_key(user_key), default)


def clear_item_state(user_key):
    key = unique_item_state_key(user_key)
    if key in g_item_state:
        del g_item_state[key]


def unique_item_state_key(user_key):
    return (g_check_type, g_checked_item, user_key)


# Idea (2): Check_MK should fetch a time stamp for each info. This should also be
# available as a global variable, so that this_time would be an optional argument.
def get_rate(user_key, this_time, this_val, allow_negative=False, onwrap=SKIP, is_rate=False):
    try:
        return get_counter(user_key, this_time, this_val, allow_negative, is_rate)[1]
    except MKCounterWrapped, e:
        if onwrap is RAISE:
            raise
        elif onwrap is SKIP:
            global g_last_counter_wrap
            g_last_counter_wrap = e
            return 0.0
        else:
            return onwrap


# Helper for get_rate(). Note: this function has been part of the official check API
# for a long time. So we cannot change its call syntax or remove it for the while.
def get_counter(countername, this_time, this_val, allow_negative=False, is_rate=False):
    old_state = get_item_state(countername, None)
    set_item_state(countername, (this_time, this_val))

    # First time we see this counter? Do not return
    # any data!
    if old_state is None:
        # Do not suppress this check on check_mk -nv
        if opt_dont_submit:
            return 1.0, 0.0
        raise MKCounterWrapped('Counter initialization')

    last_time, last_val = old_state
    timedif = this_time - last_time
    if timedif <= 0: # do not update counter
        # Do not suppress this check on check_mk -nv
        if opt_dont_submit:
            return 1.0, 0.0
        raise MKCounterWrapped('No time difference')

    if not is_rate:
        valuedif = this_val - last_val
    else:
        valuedif = this_val

    if valuedif < 0 and not allow_negative:
        # Do not try to handle wrapper counters. We do not know
        # wether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        # Do not suppress this check on check_mk -nv
        if opt_dont_submit:
            return 1.0, 0.0
        raise MKCounterWrapped('Value overflow')

    per_sec = float(valuedif) / timedif
    return timedif, per_sec


def reset_wrapped_counters():
    global g_last_counter_wrap
    g_last_counter_wrap = None


# TODO: Can we remove this? (check API)
def last_counter_wrap():
    return g_last_counter_wrap


def raise_counter_wrap():
    if g_last_counter_wrap:
        raise g_last_counter_wrap # pylint: disable=raising-bad-type


# Compute average by gliding exponential algorithm
# itemname        : unique ID for storing this average until the next check
# this_time       : timestamp of new value
# backlog         : averaging horizon in minutes
# initialize_zero : assume average of 0.0 when now previous average is stored
def get_average(itemname, this_time, this_val, backlog_minutes, initialize_zero = True):
    old_state = get_item_state(itemname, None)

    # first call: take current value as average or assume 0.0
    if old_state is None:
        if initialize_zero:
            this_val = 0
        set_item_state(itemname, (this_time, this_val))
        return this_val # avoid time diff of 0.0 -> avoid division by zero

    # Get previous value and time difference
    last_time, last_val = old_state
    timedif = this_time - last_time

    # Gracefully handle time-anomaly of target systems. We lose
    # one value, but what then heck..
    if timedif < 0:
        timedif = 0

    # Overflow error occurs if weigth exceeds 1e308 or falls below 1e-308
    # Under the conditions 0<=percentile<=1, backlog_minutes>=1 and timedif>=0
    # first case is not possible because weigth is max. 1.
    # In the second case weigth goes to zero.
    try:
        # Compute the weight: We do it like this: First we assume that
        # we get one sample per minute. And that backlog_minutes is the number
        # of minutes we should average over. Then we want that the weight
        # of the values of the last average minutes have a fraction of W%
        # in the result and the rest until infinity the rest (1-W%).
        # Then the weight can be computed as backlog_minutes'th root of 1-W
        percentile = 0.50

        weight_per_minute = (1 - percentile) ** (1.0 / backlog_minutes)

        # now let's compute the weight per second. This is done
        weight = weight_per_minute ** (timedif / 60.0)

    except OverflowError:
        weight = 0

    new_val = last_val * weight + this_val * (1 - weight)

    set_item_state(itemname, (this_time, new_val))
    return new_val




#.
#   .--Checking------------------------------------------------------------.
#   |               ____ _               _    _                            |
#   |              / ___| |__   ___  ___| | _(_)_ __   __ _                |
#   |             | |   | '_ \ / _ \/ __| |/ / | '_ \ / _` |               |
#   |             | |___| | | |  __/ (__|   <| | | | | (_| |               |
#   |              \____|_| |_|\___|\___|_|\_\_|_| |_|\__, |               |
#   |                                                 |___/                |
#   +----------------------------------------------------------------------+
#   |  Performing the actual checks                                        |
#   '----------------------------------------------------------------------'

# This is the main check function - the central entry point to all and
# everything
def do_check(hostname, ipaddress, only_check_types = None):
    cpu_tracking.start("busy")
    console.verbose("Check_MK version %s\n" % cmk.__version__)


    expected_version = agent_target_version(hostname)

    # Exit state in various situations is configurable since 1.2.3i1
    exit_spec = exit_code_spec(hostname)

    try:
        load_item_state(hostname)
        agent_version, num_success, error_sections, problems = \
            do_all_checks_on_host(hostname, ipaddress, only_check_types)

        num_errors = len(error_sections)
        save_item_state(hostname)
        if problems:
            output = "%s, " % problems
            status = exit_spec.get("connection", 2)
        elif num_errors > 0 and num_success > 0:
            output = "Missing agent sections: %s - " % ", ".join(error_sections)
            status = exit_spec.get("missing_sections", 1)
        elif num_errors > 0:
            output = "Got no information from host, "
            status = exit_spec.get("empty_output", 2)
        elif expected_version and agent_version \
             and not is_expected_agent_version(agent_version, expected_version):
            # expected version can either be:
            # a) a single version string
            # b) a tuple of ("at_least", {'daily_build': '2014.06.01', 'release': '1.2.5i4'}
            #    (the dict keys are optional)
            if type(expected_version) == tuple and expected_version[0] == 'at_least':
                expected = 'at least'
                if 'daily_build' in expected_version[1]:
                    expected += ' build %s' % expected_version[1]['daily_build']
                if 'release' in expected_version[1]:
                    if 'daily_build' in expected_version[1]:
                        expected += ' or'
                    expected += ' release %s' % expected_version[1]['release']
            else:
                expected = expected_version
            output = "unexpected agent version %s (should be %s), " % (agent_version, expected)
            status = exit_spec.get("wrong_version", 1)
        elif agent_min_version and agent_version < agent_min_version:
            output = "old plugin version %s (should be at least %s), " % (agent_version, agent_min_version)
            status = exit_spec.get("wrong_version", 1)
        else:
            output = ""
            if not is_cluster(hostname) and agent_version != None:
                output += "Agent version %s, " % agent_version
            status = 0

    except MKTimeout:
        raise

    except MKGeneralException, e:
        if cmk.debug.enabled():
            raise
        output = "%s, " % e
        status = exit_spec.get("exception", 3)

    if aggregate_check_mk:
        try:
            submit_check_mk_aggregation(hostname, status, output)
        except:
            if cmk.debug.enabled():
                raise

    if checkresult_file_fd != None:
        close_checkresult_file()

    cpu_tracking.end()
    phase_times = cpu_tracking.get_times()
    total_times = phase_times["TOTAL"]
    run_time = total_times[4]

    if check_mk_perfdata_with_times:
        output += "execution time %.1f sec|execution_time=%.3f user_time=%.3f "\
                  "system_time=%.3f children_user_time=%.3f children_system_time=%.3f" %\
                (run_time, run_time, total_times[0], total_times[1], total_times[2], total_times[3])

        for phase, times in phase_times.items():
            if phase in [ "agent", "snmp", "ds" ]:
                t = times[4] - sum(times[:4]) # real time - CPU time
                output += " cmk_time_%s=%.3f" % (phase, t)
        output += "\n"
    else:
        output += "execution time %.1f sec|execution_time=%.3f\n" % (run_time, run_time)

    if record_inline_snmp_stats and is_inline_snmp_host(hostname):
        save_snmp_stats()

    if opt_keepalive:
        add_keepalive_active_check_result(hostname, output)
        console.verbose(output)
    else:
        console.output(core_state_names[status] + " - " + output.encode('utf-8'))

    return status


def is_expected_agent_version(agent_version, expected_version):
    try:
        if agent_version in [ '(unknown)', None, 'None' ]:
            return False

        if type(expected_version) == str and expected_version != agent_version:
            return False

        elif type(expected_version) == tuple and expected_version[0] == 'at_least':
            spec = expected_version[1]
            if cmk_base.utils.is_daily_build_version(agent_version) and 'daily_build' in spec:
                expected = int(spec['daily_build'].replace('.', ''))

                branch = cmk_base.utils.branch_of_daily_build(agent_version)
                if branch == "master":
                    agent = int(agent_version.replace('.', ''))

                else: # branch build (e.g. 1.2.4-2014.06.01)
                    agent = int(agent_version.split('-')[1].replace('.', ''))

                if agent < expected:
                    return False

            elif 'release' in spec:
                if cmk_base.utils.parse_check_mk_version(agent_version) \
                    < cmk_base.utils.parse_check_mk_version(spec['release']):
                    return False

        return True
    except Exception, e:
        if cmk.debug.enabled():
            raise
        raise MKGeneralException("Unable to check agent version (Agent: %s Expected: %s, Error: %s)" %
                (agent_version, expected_version, e))


# Loops over all checks for a host, gets the data, calls the check
# function that examines that data and sends the result to the Core.
def do_all_checks_on_host(hostname, ipaddress, only_check_types = None, fetch_agent_version = True):
    global g_aggregated_service_results
    g_aggregated_service_results = {}
    global g_hostname
    g_hostname = hostname
    error_sections = set([])
    check_table = get_precompiled_check_table(hostname, remove_duplicates=True,
                                    world=opt_keepalive and "active" or "config")
    problems = []

    parsed_infos = {} # temporary cache for section infos, maybe parsed

    def execute_check(checkname, item, params, description, aggrname, ipaddress):
        if only_check_types != None and checkname not in only_check_types:
            return False

        # Make a bit of context information globally available, so that functions
        # called by checks now this context
        global g_service_description, g_check_type, g_checked_item
        g_service_description = description
        g_check_type = checkname
        g_checked_item = item

        # Skip checks that are not in their check period
        period = check_period_of(hostname, description)
        if period and not check_timeperiod(period):
            console.verbose("Skipping service %s: currently not in timeperiod %s.\n" % (description, period))
            return False

        elif period:
            console.vverbose("Service %s: timeperiod %s is currently active.\n" % (description, period))

        infotype = checkname.split('.')[0]
        try:
            if infotype in parsed_infos:
                info = parsed_infos[infotype]
            else:
                info = get_info_for_check(hostname, ipaddress, infotype)
                parsed_infos[infotype] = info

        except MKSkipCheck, e:
            return False

        except MKSNMPError, e:
            if str(e):
                problems.append(str(e))
            error_sections.add(infotype)
            g_broken_snmp_hosts.add(hostname)
            return False

        except MKAgentError, e:
            if str(e):
                problems.append(str(e))
            error_sections.add(infotype)
            g_broken_agent_hosts.add(hostname)
            return False

        except MKParseFunctionError, e:
            info = e

        # In case of SNMP checks but missing agent response, skip this check.
        # Special checks which still need to be called even with empty data
        # may declare this.
        if info == [] and check_uses_snmp(checkname) \
           and not check_info[checkname]["handle_empty_info"]:
            error_sections.add(infotype)
            return False

        if info or info in [ [], {} ]:
            try:
                check_function = check_info[checkname]["check_function"]
            except:
                check_function = check_unimplemented

            try:
                dont_submit = False

                # Call the actual check function
                reset_wrapped_counters()

                if isinstance(info, MKParseFunctionError):
                    x = info.exc_info()
                    raise x[0], x[1], x[2] # re-raise the original exception to not destory the trace

                result = sanitize_check_result(check_function(item, params, info), check_uses_snmp(checkname))
                raise_counter_wrap()


            # handle check implementations that do not yet support the
            # handling of wrapped counters via exception. Do not submit
            # any check result in that case:
            except MKCounterWrapped, e:
                console.verbose("%-20s PEND - Cannot compute check result: %s\n" % (description, e))
                dont_submit = True

            except Exception, e:
                if cmk.debug.enabled():
                    raise
                result = 3, create_crash_dump(hostname, checkname, item, params, description, info), []

            if not dont_submit:
                # Now add information about the age of the data in the agent
                # sections. This is in g_agent_cache_info. For clusters we
                # use the oldest of the timestamps, of course.
                oldest_cached_at = None
                largest_interval = None

                def minn(a, b):
                    if a == None:
                        return b
                    elif b == None:
                        return a
                    return min(a,b)

                for section_entries in g_agent_cache_info.values():
                    if infotype in section_entries:
                        cached_at, cache_interval = section_entries[infotype]
                        oldest_cached_at = minn(oldest_cached_at, cached_at)
                        largest_interval = max(largest_interval, cache_interval)

                submit_check_result(hostname, description, result, aggrname,
                                    cached_at=oldest_cached_at, cache_interval=largest_interval)
            return True
        else:
            error_sections.add(infotype)
            return False

    num_success = 0

    if has_management_board(hostname):
        # this assumes all snmp checks belong to the management board if there is one with snmp
        # protocol. If at some point we support having both host and management board queried
        # through snmp we have to decide which check belongs where at discovery time and change
        # all data structures, including in the nagios interface...
        is_management_snmp = management_protocol(hostname) == "snmp"
        management_addr = management_address(hostname)
    else:
        is_management_snmp = False

    for checkname, item, params, description, aggrname in check_table:
        if is_snmp_check(checkname) and is_management_snmp:
            address = management_addr
        else:
            address = ipaddress

        res = execute_check(checkname, item, params, description, aggrname, address)
        if res:
            num_success += 1

    submit_aggregated_results(hostname)

    if fetch_agent_version:
        try:
            if is_tcp_host(hostname):
                version_info = get_info_for_check(hostname, ipaddress, 'check_mk')
                agent_version = version_info[0][1]
            else:
                agent_version = None
        except MKAgentError:
            g_broken_agent_hosts.add(hostname)
            agent_version = "(unknown)"
        except:
            agent_version = "(unknown)"
    else:
        agent_version = None

    error_section_list = sorted(list(error_sections))

    return agent_version, num_success, error_section_list, ", ".join(problems)


# Create a crash dump with a backtrace and the agent output.
# This is put into a directory per service. The content is then
# put into a tarball, base64 encoded and put into the long output
# of the check :-)
def create_crash_dump(hostname, check_type, item, params, description, info):
    text = "check failed - please submit a crash report!"
    try:
        crash_dir = cmk.paths.var_dir + "/crashed_checks/" + hostname + "/" + description.replace("/", "\\")
        prepare_crash_dump_directory(crash_dir)

        create_crash_dump_info_file(crash_dir, hostname, check_type, item, params, description, info, text)
        if check_uses_snmp(check_type):
            write_crash_dump_snmp_info(crash_dir, hostname, check_type)
        else:
            write_crash_dump_agent_output(crash_dir, hostname)

        text += "\n" + "Crash dump:\n" + pack_crash_dump(crash_dir) + "\n"
    except:
        if cmk.debug.enabled():
            raise

    return text


def prepare_crash_dump_directory(crash_dir):
    if not os.path.exists(crash_dir):
        os.makedirs(crash_dir)
    # Remove all files of former crash reports
    for f in os.listdir(crash_dir):
        try:
            os.unlink(crash_dir + "/" + f)
        except OSError:
            pass


def is_manual_check(hostname, check_type, item):
    # In case of nagios we don't have this information available (in precompiled mode)
    if not "get_check_table" in globals():
        return None

    manual_checks = get_check_table(hostname, remove_duplicates=True,
                                    world=opt_keepalive and "active" or "config",
                                    skip_autochecks=True)
    return (check_type, item) in manual_checks


def initialize_check_type_caches():
    snmp_cache = cmk_base.config_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info.keys())

    tcp_cache = cmk_base.config_cache.get_set("check_type_tcp")
    tcp_cache.update(check_info.keys())


def is_snmp_check(check_name):
    cache = cmk_base.config_cache.get_dict("is_snmp_check")

    try:
        return cache[check_name]
    except KeyError:
        snmp_checks = cmk_base.config_cache.get_set("check_type_snmp")

        result = check_name.split(".")[0] in snmp_checks
        cache[check_name] = result
        return result


def is_tcp_check(check_name):
    cache = cmk_base.config_cache.get_dict("is_tcp_check")

    try:
        return cache[check_name]
    except KeyError:
        tcp_checks = cmk_base.config_cache.get_set("check_type_tcp")
        snmp_checks = cmk_base.config_cache.get_set("check_type_snmp")

        result = check_name in tcp_checks \
                  and check_name.split(".")[0] not in snmp_checks # snmp check basename
        cache[check_name] = result
        return result


def create_crash_dump_info_file(crash_dir, hostname, check_type, item, params, description, info, text):
    crash_info = crash_reporting.create_crash_info("check", details={
        "check_output"  : text,
        "host"          : hostname,
        "is_cluster"    : is_cluster(hostname),
        "description"   : description,
        "check_type"    : check_type,
        "item"          : item,
        "params"        : params,
        "uses_snmp"     : check_uses_snmp(check_type),
        "inline_snmp"   : is_inline_snmp_host(hostname),
        "manual_check"  : is_manual_check(hostname, check_type, item),
    })
    file(crash_dir+"/crash.info", "w").write(crash_reporting.crash_info_to_string(crash_info)+"\n")


def write_crash_dump_snmp_info(crash_dir, hostname, check_type):
    cachefile = cmk.paths.tcp_cache_dir + "/" + hostname + "." + check_type.split(".")[0]
    if os.path.exists(cachefile):
        file(crash_dir + "/snmp_info", "w").write(file(cachefile).read())


def write_crash_dump_agent_output(crash_dir, hostname):
    if "get_rtc_package" in globals():
        file(crash_dir + "/agent_output", "w").write(get_rtc_package())
    else:
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname
        if os.path.exists(cachefile):
            file(crash_dir + "/agent_output", "w").write(file(cachefile).read())


def pack_crash_dump(crash_dir):
    import base64
    tarcontent = os.popen("cd %s ; tar czf - *" % quote_shell_string(crash_dir)).read()
    return base64.b64encode(tarcontent)


def check_unimplemented(checkname, params, info):
    return (3, 'UNKNOWN - Check not implemented')


# FIXME: Clear / unset all legacy variables to prevent confusions in other code trying to
# use the legacy variables which are not set by newer checks.
def convert_check_info():
    check_info_defaults = {
        "check_function"          : check_unimplemented,
        "inventory_function"      : None,
        "parse_function"          : None,
        "group"                   : None,
        "snmp_info"               : None,
        "snmp_scan_function"      : None,
        "handle_empty_info"       : False,
        "handle_real_time_checks" : False,
        "default_levels_variable" : None,
        "node_info"               : False,
        "extra_sections"          : [],
        "service_description"     : None,
        "has_perfdata"            : False,
    }

    for check_type, info in check_info.items():
        basename = check_type.split(".")[0]

        if type(info) != dict:
            # Convert check declaration from old style to new API
            check_function, service_description, has_perfdata, inventory_function = info
            if inventory_function == no_discovery_possible:
                inventory_function = None

            check_info[check_type] = {
                "check_function"          : check_function,
                "service_description"     : service_description,
                "has_perfdata"            : not not has_perfdata,
                "inventory_function"      : inventory_function,
                # Insert check name as group if no group is being defined
                "group"                   : checkgroup_of.get(check_type, check_type),
                "snmp_info"               : snmp_info.get(check_type),
                # Sometimes the scan function is assigned to the check_type
                # rather than to the base name.
                "snmp_scan_function"      :
                    snmp_scan_functions.get(check_type,
                        snmp_scan_functions.get(basename)),
                "handle_empty_info"       : False,
                "handle_real_time_checks" : False,
                "default_levels_variable" : check_default_levels.get(check_type),
                "node_info"               : False,
                "parse_function"          : None,
                "extra_sections"          : [],
            }
        else:
            # Ensure that there are only the known keys set. Is meant to detect typos etc.
            for key in info.keys():
                if key != "includes" and key not in check_info_defaults:
                    raise MKGeneralException("The check '%s' declares an unexpected key '%s' in 'check_info'." %
                                                                                    (check_type, key))

            # Check does already use new API. Make sure that all keys are present,
            # extra check-specific information into file-specific variables.
            for key, val in check_info_defaults.items():
                info.setdefault(key, val)

            # Include files are related to the check file (= the basename),
            # not to the (sub-)check. So we keep them in check_includes.
            check_includes.setdefault(basename, [])
            check_includes[basename] += info.get("includes", [])

    # Make sure that setting for node_info of check and subcheck matches
    for check_type, info in check_info.iteritems():
        if "." in check_type:
            base_check = check_type.split(".")[0]
            if base_check not in check_info:
                if info["node_info"]:
                    raise MKGeneralException("Invalid check implementation: node_info for %s is True, but base check %s not defined" %
                        (check_type, base_check))
            elif check_info[base_check]["node_info"] != info["node_info"]:
               raise MKGeneralException("Invalid check implementation: node_info for %s and %s are different." % (
                   (base_check, check_type)))

    # Now gather snmp_info and snmp_scan_function back to the
    # original arrays. Note: these information is tied to a "agent section",
    # not to a check. Several checks may use the same SNMP info and scan function.
    for check_type, info in check_info.iteritems():
        basename = check_type.split(".")[0]
        if info["snmp_info"] and basename not in snmp_info:
            snmp_info[basename] = info["snmp_info"]
        if info["snmp_scan_function"] and basename not in snmp_scan_functions:
            snmp_scan_functions[basename] = info["snmp_scan_function"]


def sanitize_check_result(result, is_snmp):
    if type(result) == tuple:
        return sanitize_tuple_check_result(result)

    elif result == None:
        return item_not_found(is_snmp)

    else:
        return sanitize_yield_check_result(result, is_snmp)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def sanitize_yield_check_result(result, is_snmp):
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return item_not_found(is_snmp)

    # Simple check with no separate subchecks (yield wouldn't have been neccessary here!)
    if len(subresults) == 1:
        state, infotext, perfdata = sanitize_tuple_check_result(subresults[0], allow_missing_infotext=True)
        if infotext == None:
            return state, u"", perfdata
        else:
            return state, infotext, perfdata

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    else:
        perfdata = []
        infotexts = []
        status = 0

        for subresult in subresults:
            st, text, perf = sanitize_tuple_check_result(subresult, allow_missing_infotext=True)

            # FIXME/TODO: Why is the state only aggregated when having text != None?
            if text != None:
                infotexts.append(text + ["", "(!)", "(!!)", "(?)"][st])
                status = worst_monitoring_state(st, status)

            if perf != None:
                perfdata += subresult[2]

        return status, ", ".join(infotexts), perfdata


def item_not_found(is_snmp):
    if is_snmp:
        return 3, "Item not found in SNMP data", []
    else:
        return 3, "Item not found in agent output", []


def sanitize_tuple_check_result(result, allow_missing_infotext=False):
    if len(result) >= 3:
        state, infotext, perfdata = result[:3]
    else:
        state, infotext = result
        perfdata = None

    infotext = sanitize_check_result_infotext(infotext, allow_missing_infotext)

    return state, infotext, perfdata


def sanitize_check_result_infotext(infotext, allow_missing_infotext):
    if infotext == None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if type(infotext) == str:
        return infotext.decode('utf-8')
    else:
        return infotext


def open_checkresult_file():
    global checkresult_file_fd
    global checkresult_file_path
    if checkresult_file_fd == None:
        try:
            checkresult_file_fd, checkresult_file_path = \
                tempfile.mkstemp('', 'c', cmk.paths.check_result_path)
        except Exception, e:
            raise MKGeneralException("Cannot create check result file in %s: %s" %
                    (cmk.paths.check_result_path, e))


def close_checkresult_file():
    global checkresult_file_fd
    if checkresult_file_fd != None:
        os.close(checkresult_file_fd)
        file(checkresult_file_path + ".ok", "w")
        checkresult_file_fd = None


def core_pipe_open_timeout(signum, stackframe):
    raise IOError("Timeout while opening pipe")


def open_command_pipe():
    global nagios_command_pipe
    if nagios_command_pipe == None:
        if not os.path.exists(cmk.paths.nagios_command_pipe_path):
            nagios_command_pipe = False # False means: tried but failed to open
            raise MKGeneralException("Missing core command pipe '%s'" % cmk.paths.nagios_command_pipe_path)
        else:
            try:
                signal.signal(signal.SIGALRM, core_pipe_open_timeout)
                signal.alarm(3) # three seconds to open pipe
                nagios_command_pipe =  file(cmk.paths.nagios_command_pipe_path, 'w')
                signal.alarm(0) # cancel alarm
            except Exception, e:
                nagios_command_pipe = False
                raise MKGeneralException("Error writing to command pipe: %s" % e)


def convert_perf_value(x):
    if x == None:
        return ""
    elif type(x) in [ str, unicode ]:
        return x
    elif type(x) == float:
        return ("%.6f" % x).rstrip("0").rstrip(".")
    else:
        return str(x)


def convert_perf_data(p):
    # replace None with "" and fill up to 7 values
    p = (map(convert_perf_value, p) + ['','','',''])[0:6]
    return "%s=%s;%s;%s;%s;%s" %  tuple(p)


def submit_check_result(host, servicedesc, result, sa, cached_at=None, cache_interval=None):
    if not result:
        result = 3, "Check plugin did not return any result"

    if len(result) != 3:
        raise MKGeneralException("Invalid check result: %s" % (result, ))
    state, infotext, perfdata = result

    if not (
        infotext.startswith("OK -") or
        infotext.startswith("WARN -") or
        infotext.startswith("CRIT -") or
        infotext.startswith("UNKNOWN -")):
        infotext = core_state_names[state] + " - " + infotext

    # make sure that plugin output does not contain a vertical bar. If that is the
    # case then replace it with a Uniocode "Light vertical bar
    if isinstance(infotext, unicode):
        # regular check results are unicode...
        infotext = infotext.replace(u"|", u"\u2758")
    else:
        # ...crash dumps, and hard-coded outputs are regular strings
        infotext = infotext.replace("|", u"\u2758".encode("utf8"))

    # Aggregated service -> store for later
    if sa != "":
        store_aggregated_service_result(host, servicedesc, sa, state, infotext)

    # performance data - if any - is stored in the third part of the result
    perftexts = []
    perftext = ""

    if perfdata:
        # Check may append the name of the check command to the
        # list of perfdata. It is of type string. And it might be
        # needed by the graphing tool in order to choose the correct
        # template. Currently this is used only by mrpe.
        if len(perfdata) > 0 and type(perfdata[-1]) in (str, unicode):
            check_command = perfdata[-1]
            del perfdata[-1]
        else:
            check_command = None

        for p in perfdata:
            perftexts.append(convert_perf_data(p))

        if perftexts != []:
            if check_command and perfdata_format == "pnp":
                perftexts.append("[%s]" % check_command)
            perftext = "|" + (" ".join(perftexts))

    if not opt_dont_submit:
        submit_to_core(host, servicedesc, state, infotext + perftext, cached_at, cache_interval)

    output_check_result(servicedesc, state, infotext, perftexts)


def output_check_result(servicedesc, state, infotext, perftexts):
    if not logger.is_verbose():
        return

    if opt_showperfdata:
        infotext_fmt = "%-56s"
        p = ' (%s)' % (" ".join(perftexts))
    else:
        p = ''
        infotext_fmt = "%s"

    console.verbose("%-20s %s%s"+infotext_fmt+"%s%s\n",
        servicedesc.encode('utf-8'), tty.bold, tty.states[state],
        make_utf8(infotext.split('\n')[0]),
        tty.normal, make_utf8(p))


def submit_to_core(host, service, state, output, cached_at = None, cache_interval = None):
    if opt_keepalive:
        # Regular case for the CMC - check helpers are running in keepalive mode
        add_keepalive_check_result(host, service, state, output, cached_at, cache_interval)

    elif check_submission == "pipe" or monitoring_core == "cmc":
        # In case of CMC this is used when running "cmk" manually
        submit_via_command_pipe(host, service, state, output)

    elif check_submission == "file":
        submit_via_check_result_file(host, service, state, output)

    else:
        raise MKGeneralException("Invalid setting %r for check_submission. "
                                 "Must be 'pipe' or 'file'" % check_submission)


def submit_via_check_result_file(host, service, state, output):
    output = output.replace("\n", "\\n")
    open_checkresult_file()
    if checkresult_file_fd:
        now = time.time()
        os.write(checkresult_file_fd,
                """host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

""" % (host, make_utf8(service), now, now, state, make_utf8(output)))


def submit_via_command_pipe(host, service, state, output):
    output = output.replace("\n", "\\n")
    open_command_pipe()
    if nagios_command_pipe:
        # [<timestamp>] PROCESS_SERVICE_CHECK_RESULT;<host_name>;<svc_description>;<return_code>;<plugin_output>
        nagios_command_pipe.write("[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" %
                               (int(time.time()), host, make_utf8(service), state, make_utf8(output)))
        # Important: Nagios needs the complete command in one single write() block!
        # Python buffers and sends chunks of 4096 bytes, if we do not flush.
        nagios_command_pipe.flush()


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Some generic helper functions                                       |
#   +----------------------------------------------------------------------+

def make_utf8(x):
    if type(x) == unicode:
        return x.encode('utf-8')
    else:
        return x


def i_am_root():
    return os.getuid() == 0

# Returns the nodes of a cluster, or None if hostname is
# not a cluster
def nodes_of(hostname):
    nodes_of_cache = cmk_base.config_cache.get_dict("nodes_of")
    nodes = nodes_of_cache.get(hostname, False)
    if nodes != False:
        return nodes

    for tagged_hostname, nodes in clusters.items():
        if hostname == tagged_hostname.split("|")[0]:
            nodes_of_cache[hostname] = nodes
            return nodes

    nodes_of_cache[hostname] = None
    return None

def check_uses_snmp(check_type):
    info_type = check_type.split(".")[0]
    return snmp_info.get(info_type) != None or \
       (info_type in inv_info and "snmp_info" in inv_info[info_type])


def worst_monitoring_state(status_a, status_b):
    if status_a == 2 or status_b == 2:
        return 2
    else:
        return max(status_a, status_b)


def set_use_cachefile(state=True):
    global opt_use_cachefile, orig_opt_use_cachefile
    orig_opt_use_cachefile = opt_use_cachefile
    opt_use_cachefile = state


# Creates the directory at path if it does not exist.  If that path does exist
# it is assumed that it is a directory. the file type is not being checked.
# This function is atomar so that no exception can arise if two processes
# at the same time try to create the directory. Only fails if the directory
# is not present for any reason after this function call.
def ensure_directory(path):
    try:
        os.makedirs(path)
    except Exception:
        if os.path.exists(path):
            return
        raise

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

#.
#   .--Check helpers-------------------------------------------------------.
#   |     ____ _               _      _          _                         |
#   |    / ___| |__   ___  ___| | __ | |__   ___| |_ __   ___ _ __ ___     |
#   |   | |   | '_ \ / _ \/ __| |/ / | '_ \ / _ \ | '_ \ / _ \ '__/ __|    |
#   |   | |___| | | |  __/ (__|   <  | | | |  __/ | |_) |  __/ |  \__ \    |
#   |    \____|_| |_|\___|\___|_|\_\ |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                                             |_|                      |
#   +----------------------------------------------------------------------+
#   |  Helper function for being used in checks                            |
#   '----------------------------------------------------------------------'


# Use this function to get the age of the agent data cache file
# of tcp or snmp hosts or None in case of piggyback data because
# we do not exactly know the latest agent data. Maybe one time
# we can handle this. For cluster hosts an exception is raised.
def get_agent_data_time():
    return agent_cache_file_age(g_hostname, g_check_type)


def agent_cache_file_age(hostname, check_type):
    if is_cluster(hostname):
        raise MKGeneralException("get_agent_data_time() not valid for cluster")

    if is_snmp_check(check_type):
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname + "." + check_type.split(".")[0]
    elif is_tcp_check(check_type):
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname
    else:
        cachefile = None

    if cachefile is not None and os.path.exists(cachefile):
        return cachefile_age(cachefile)
    else:
        return None


# Generic function for checking a value against levels. This also supports
# predictive levels.
# value:   currently measured value
# dsname:  name of the datasource in the RRD that corresponds to this value
# unit:    unit to be displayed in the plugin output, e.g. "MB/s"
# factor:  the levels are multiplied with this factor before applying
#          them to the value. This is being used for the CPU load check
#          currently. The levels here are "per CPU", so the number of
#          CPUs is used as factor.
# scale:   Scale of the levels in relation to "value" and the value in the RRDs.
#          For example if the levels are specified in GB and the RRD store KB, then
#          the scale is 1024*1024.
def check_levels(value, dsname, params, unit="", factor=1.0, scale=1.0, statemarkers=False):
    if unit:
        unit = " " + unit # Insert space before MB, GB, etc.
    perfdata  = []
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
                cmk_base.prediction.get_levels(g_hostname, g_service_description,
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
            if cmk.debug.enabled():
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


# check range, values might be negative!
# returns True, if value is inside the interval
def within_range(value, minv, maxv):
    if value >= 0:
        return value >= minv and value <= maxv
    else:
        return value <= minv and value >= maxv

# int() function that return 0 for strings the
# cannot be converted to a number
def saveint(i):
    try:
        return int(i)
    except:
        return 0

# This variant of int() lets the string if its not
# convertable. Useful for parsing dict-like things, where
# some of the values are int.
def tryint(x):
    try:
        return int(x)
    except:
        return x


def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0

# Convert a string to an integer. This is done by consideren the string to by a
# little endian byte string.  Such strings are sometimes used by SNMP to encode
# 64 bit counters without needed COUNTER64 (which is not available in SNMP v1)
def binstring_to_int(binstring):
    value = 0
    mult = 1
    for byte in binstring[::-1]:
        value += mult * ord(byte)
        mult *= 256
    return value

get_bytes_human_readable = render.bytes

# Similar to get_bytes_human_readable, but optimized for file
# sizes. Really only use this for files. We assume that for smaller
# files one wants to compare the exact bytes of a file, so the
# threshold to show the value as MB/GB is higher as the one of
# get_bytes_human_readable().
def get_filesize_human_readable(size):
    if size < 4 * 1024 * 1024:
        return "%d B" % int(size)
    elif size < 4 * 1024 * 1024 * 1024:
        return "%.2f MB" % (float(size) / (1024 * 1024))
    else:
        return "%.2f GB" % (float(size) / (1024 * 1024 * 1024))


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


def get_timestamp_human_readable(timestamp):
    if timestamp:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    else:
        return "never"


# Format time difference seconds into approximated
# human readable value
def get_age_human_readable(secs):
    if secs < 240:
        return "%d sec" % secs
    mins = secs / 60
    if mins < 120:
        return "%d min" % mins
    hours, mins = divmod(mins, 60)
    if hours < 12 and mins > 0:
        return "%d hours %d min" % (hours, mins)
    elif hours < 48:
        return "%d hours" % hours
    days, hours = divmod(hours, 24)
    if days < 7 and hours > 0:
        return "%d days %d hours" % (days, hours)
    return "%d days" % days


def get_relative_date_human_readable(timestamp):
    now = time.time()
    if timestamp > now:
        return "in " + get_age_human_readable(timestamp - now)
    else:
        return get_age_human_readable(now - timestamp) + " ago"

# Format perc (0 <= perc <= 100 + x) so that precision
# digits are being displayed. This avoids a "0.00%" for
# very small numbers
def get_percent_human_readable(perc, precision=2):
    if perc > 0:
        perc_precision = max(1, 2 - int(round(math.log(perc, 10))))
    else:
        perc_precision = 1
    return "%%.%df%%%%" % perc_precision % perc


# Quote string for use as arguments on the shell
def quote_shell_string(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"

# ThisIsACamel -> this_is_a_camel
def camelcase_to_underscored(name):
    previous_lower = False
    previous_underscore = True
    result = ""
    for c in name:
        if c.isupper():
            if previous_lower and not previous_underscore:
                result += "_"
            previous_lower = False
            previous_underscore = False
            result += c.lower()
        elif c == "_":
            previous_lower = False
            previous_underscore = True
            result += c
        else:
            previous_lower = True
            previous_underscore = False
            result += c
    return result


# Return plain response from local Livestatus - without any parsing
# TODO: Use livestatus module
def simple_livestatus_query(lql):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(cmk.paths.livestatus_unix_socket)
    # We just get the currently inactive timeperiods. All others
    # (also non-existing) are considered to be active
    s.send(lql)
    s.shutdown(socket.SHUT_WR)
    response = ""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    return response


# Check if a timeperiod is currently active. We have no other way than
# doing a Livestatus query. This is not really nice, but if you have a better
# idea, please tell me...
def check_timeperiod(timeperiod):
    global g_inactive_timerperiods
    # Let exceptions happen, they will be handled upstream.
    if g_inactive_timerperiods == None:
        try:
            response = simple_livestatus_query("GET timeperiods\nColumns: name\nFilter: in = 0\n")
            g_inactive_timerperiods = response.splitlines()
        except MKTimeout:
            raise

        except Exception:
            if cmk.debug.enabled():
                raise
            else:
                # If the query is not successful better skip this check then fail
                return True

    return timeperiod not in g_inactive_timerperiods


# retrive the service level that applies to the calling check.
def get_effective_service_level():
    service_levels = service_extra_conf(g_hostname, g_service_description,
                                        service_service_levels)

    if service_levels:
        return service_levels[0]
    else:
        service_levels = host_extra_conf(g_hostname, host_service_levels)
        if service_levels:
            return service_levels[0]
    return 0


#.
#   .--Aggregation---------------------------------------------------------.
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   +----------------------------------------------------------------------+
#   |  Service aggregation will be removed soon now.                       |
#   '----------------------------------------------------------------------'

# Compute the name of a summary host
def summary_hostname(hostname):
    return aggr_summary_hostname % hostname

# Updates the state of an aggregated service check from the output of
# one of the underlying service checks. The status of the aggregated
# service will be updated such that the new status is the maximum
# (crit > unknown > warn > ok) of all underlying status. Appends the output to
# the output list and increases the count by 1.
def store_aggregated_service_result(hostname, detaildesc, aggrdesc, newstatus, newoutput):
    count, status, outputlist = g_aggregated_service_results.get(aggrdesc, (0, 0, []))
    if status_worse(newstatus, status):
        status = newstatus
    if newstatus > 0 or aggregation_output_format == "multiline":
        outputlist.append( (newstatus, detaildesc, newoutput) )
    g_aggregated_service_results[aggrdesc] = (count + 1, status, outputlist)

def status_worse(newstatus, status):
    if status == 2:
        return False # nothing worse then critical
    elif newstatus == 2:
        return True  # nothing worse then critical
    else:
        return newstatus > status # 0 < 1 < 3 are in correct order

# Submit the result of all aggregated services of a host
# to the core. Those are stored in g_aggregated_service_results
def submit_aggregated_results(hostname):
    if not host_is_aggregated(hostname):
        return

    console.verbose("\n%s%sAggregates Services:%s\n" % (tty.bold, tty.blue, tty.normal))

    items = g_aggregated_service_results.items()
    items.sort()
    aggr_hostname = summary_hostname(hostname)
    for servicedesc, (count, status, outputlist) in items:
        if aggregation_output_format == "multiline":
            longoutput = ""
            statuscounts = [ 0, 0, 0, 0 ]
            for itemstatus, item, output in outputlist:
                longoutput += '\\n%s: %s' % (item, output)
                statuscounts[itemstatus] = statuscounts[itemstatus] + 1
            summarytexts = [ "%d service%s %s" % (x[0], x[0] != 1 and "s" or "", x[1])
                           for x in zip(statuscounts, ["OK", "WARN", "CRIT", "UNKNOWN" ]) if x[0] > 0 ]
            text = ", ".join(summarytexts) + longoutput
        else:
            if status == 0:
                text = "OK - %d services OK" % count
            else:
                text = " *** ".join([ item + " " + output for itemstatus, item, output in outputlist ])

        if not opt_dont_submit:
            submit_to_core(aggr_hostname, servicedesc, status, text)

        output_check_result(servicedesc, status, text, [])


def submit_check_mk_aggregation(hostname, status, output):
    if not host_is_aggregated(hostname):
        return

    if not opt_dont_submit:
        submit_to_core(summary_hostname(hostname), "Check_MK", status, output)

    console.verbose("%-20s %s%s%-70s%s\n" % ("Check_MK", tty.bold, tty.states[status], output, tty.normal))


#.
#   .--Ctrl-C--------------------------------------------------------------.
#   |                     ____ _        _        ____                      |
#   |                    / ___| |_ _ __| |      / ___|                     |
#   |                   | |   | __| '__| |_____| |                         |
#   |                   | |___| |_| |  | |_____| |___                      |
#   |                    \____|\__|_|  |_|      \____|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Handling of Ctrl-C                                                  |
#   '----------------------------------------------------------------------'

# register SIGINT handler for consistent CTRL+C handling
# TODO: use MKTerminate() signal instead and handle output and exit code in check_mk.py
def interrupt_handler(signum, frame):
    console.output('<Interrupted>\n', stream=sys.stderr)
    sys.exit(1)


def register_sigint_handler():
    signal.signal(signal.SIGINT, interrupt_handler)



# register SIGINT handler for consistent CTRL+C handling
def handle_keepalive_interrupt(signum, frame):
    raise MKTerminate()


def register_keepalive_sigint_handler():
    signal.signal(signal.SIGINT, handle_keepalive_interrupt)
