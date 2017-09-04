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

import os
import signal
import socket
import subprocess
import sys
import time

import cmk.paths
import cmk.debug
import cmk.cpu_tracking as cpu_tracking
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk.store as store
import cmk_base.config as config
import cmk_base.rulesets as rulesets
import cmk_base.console as console
import cmk_base.checks as checks
import cmk_base.item_state as item_state
import cmk_base.ip_lookup as ip_lookup
import cmk_base.piggyback as piggyback
import cmk_base.snmp as snmp
import cmk_base.core_config as core_config
from cmk_base.exceptions import MKSkipCheck, MKAgentError, MKSNMPError, \
                                MKParseFunctionError, MKTimeout

g_infocache                  = {} # In-memory cache of host info.
g_agent_cache_info           = {} # Information about agent caching
g_agent_already_contacted    = {} # do we have agent data from this host?
g_broken_snmp_hosts          = set()
g_broken_agent_hosts         = set()

_no_cache                    = False
_no_tcp                      = False
_no_submit                   = False
_enforce_persisting          = False

def get_info_for_check(hostname, ipaddress, section_name,
                       max_cachefile_age=None, ignore_check_interval=False):
    info = apply_parse_function(_get_host_info(hostname, ipaddress, section_name, max_cachefile_age, ignore_check_interval), section_name)
    if info != None and section_name in checks.check_info and checks.check_info[section_name]["extra_sections"]:
        info = [ info ]
        for es in checks.check_info[section_name]["extra_sections"]:
            try:
                info.append(apply_parse_function(_get_host_info(hostname, ipaddress, es, max_cachefile_age, ignore_check_interval=False), es))
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


def _get_host_info(hostname, ipaddress, checkname, max_cachefile_age=None, ignore_check_interval=False):
    # If the check want's the node info, we add an additional
    # column (as the first column) with the name of the node
    # or None (in case of non-clustered nodes). On problem arises,
    # if we deal with subchecks. We assume that all subchecks
    # have the same setting here. If not, let's raise an exception.
    has_nodeinfo = checks.check_info.get(checkname, {}).get("node_info", False)

    nodes = config.nodes_of(hostname)
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
                ipaddress = ip_lookup.lookup_ip_address(node)
                new_info = get_realhost_info(node, ipaddress, checkname,
                               max_cachefile_age == None and config.cluster_max_cachefile_age or max_cachefile_age,
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
                      max_cachefile_age == None and config.check_max_cachefile_age or max_cachefile_age,
                      ignore_check_interval)
        if info != None and has_nodeinfo:
            if config.clusters_of(hostname):
                add_host = hostname
            else:
                add_host = None
            info = add_nodeinfo(info, add_host)

    return info


def apply_parse_function(info, section_name):
    # Now some check types define a parse function. In that case the
    # info is automatically being parsed by that function - on the fly.
    if info != None and section_name in checks.check_info:
        parse_function = checks.check_info[section_name]["parse_function"]
        if parse_function:
            try:
                item_state.set_item_state_prefix(section_name, None)
                return parse_function(info)
            except Exception:
                if cmk.debug.enabled():
                    raise

                # In case of a failed parse function return the exception instead of
                # an empty result.
                raise MKParseFunctionError(*sys.exc_info())

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
    import cmk_base.inventory_plugins as inventory_plugins

    info = _get_cached_hostinfo(hostname)
    if info and info.has_key(check_type):
        return info[check_type]

    cache_relpath = hostname + "." + check_type

    # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
    # Please note, that if the check_type is foo.bar then we lookup the
    # snmp info for "foo", not for "foo.bar".
    info_type = check_type.split(".")[0]
    if info_type in checks.snmp_info:
        oid_info = checks.snmp_info[info_type]
    elif info_type in inventory_plugins.inv_info:
        oid_info = inventory_plugins.inv_info[info_type].get("snmp_info")
    else:
        oid_info = None

    if oid_info:
        cache_path = cmk.paths.tcp_cache_dir + "/" + cache_relpath

        # Handle SNMP check interval. The idea: An SNMP check should only be
        # executed every X seconds. Skip when called too often.
        check_interval = config.check_interval_of(hostname, check_type)
        if not ignore_check_interval \
           and not _no_submit \
           and check_interval is not None and os.path.exists(cache_path) \
           and cmk_base.utils.cachefile_age(cache_path) < check_interval * 60:
            # cache file is newer than check_interval, skip this check
            raise MKSkipCheck()

        try:
            content = read_cache_file(cache_relpath, max_cache_age)
        except:
            if config.simulation_mode and not _no_cache:
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
            table = [ snmp.get_snmp_table(hostname, ipaddress, check_type, entry, use_snmpwalk_cache) for entry in oid_info ]
            # if at least one query fails, we discard the hole table
            if None in table:
                table = None
        else:
            table = snmp.get_snmp_table(hostname, ipaddress, check_type, oid_info, use_snmpwalk_cache)

        _store_cached_checkinfo(hostname, check_type, table)

        # only write cache file in non interactive mode. Otherwise it would
        # prevent the regular checking from getting status updates during
        # interactive debugging, for example with cmk -nv.
        # TODO: Why is SNMP different from TCP/Datasource handling?
        if not _no_submit:
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
    piggy_output = piggyback.get_piggyback_info(hostname) \
                 + piggyback.get_piggyback_info(ipaddress)

    output = ""
    agent_failed_exc = None
    if config.is_tcp_host(hostname):
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
            piggyback.remove_piggyback_info_from(hostname)

            if not piggy_output:
                raise
            elif cmk.debug.enabled():
                raise

    output += piggy_output

    if len(output) == 0 and config.is_tcp_host(hostname):
        raise MKAgentError("Empty output from agent")
    elif len(output) == 0:
        return
    elif len(output) < 16:
        raise MKAgentError("Too short output from agent: '%s'" % output)

    info, piggybacked, persisted, agent_cache_info = parse_info(output.split("\n"), hostname)
    g_agent_cache_info.setdefault(hostname, {}).update(agent_cache_info)
    piggyback.store_piggyback_info(hostname, piggybacked)
    _store_persisted_info(hostname, persisted)
    store_cached_hostinfo(hostname, info)

    # Add information from previous persisted agent outputs, if those
    # sections are not available in the current output
    # TODO: In the persisted sections the agent_cache_info is missing
    _add_persisted_info(hostname, info)

    # If the agent has failed and the information we seek is
    # not contained in the piggy data, raise an exception
    if check_type not in info:
        if agent_failed_exc:
            raise MKAgentError("Cannot get information from agent (%s), processing only piggyback data." % agent_failed_exc)
        else:
            return []

    return info[check_type] # return only data for specified check


#.
#   .--Parsing-------------------------------------------------------------.
#   |                  ____                _                               |
#   |                 |  _ \ __ _ _ __ ___(_)_ __   __ _                   |
#   |                 | |_) / _` | '__/ __| | '_ \ / _` |                  |
#   |                 |  __/ (_| | |  \__ \ | | | | (_| |                  |
#   |                 |_|   \__,_|_|  |___/_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   | Parsing of raw agent data bytes into data structures                 |
#   '----------------------------------------------------------------------'

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
                host = piggyback.translate_piggyback_host(hostname, host)
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
                line = config.decode_incoming_string(line, encoding)
            else:
                line = config.decode_incoming_string(line)

            section.append(line.split(separator))

    return info, piggybacked, persist, agent_cache_info


#.
#   .--MemoryCache---------------------------------------------------------.
#   |  __  __                                  ____           _            |
#   | |  \/  | ___ _ __ ___   ___  _ __ _   _ / ___|__ _  ___| |__   ___   |
#   | | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | | |   / _` |/ __| '_ \ / _ \  |
#   | | |  | |  __/ | | | | | (_) | |  | |_| | |__| (_| | (__| | | |  __/  |
#   | |_|  |_|\___|_| |_| |_|\___/|_|   \__, |\____\__,_|\___|_| |_|\___|  |
#   |                                   |___/                              |
#   +----------------------------------------------------------------------+
#   | In memory caching of host info data during a single exceution        |
#   '----------------------------------------------------------------------'

# Gets all information about one host so far cached.
# Returns None if nothing has been stored so far
def _get_cached_hostinfo(hostname):
    return g_infocache.get(hostname, None)

# store complete information about a host
def store_cached_hostinfo(hostname, info):
    oldinfo = _get_cached_hostinfo(hostname)
    if oldinfo:
        oldinfo.update(info)
        g_infocache[hostname] = oldinfo
    else:
        g_infocache[hostname] = info

# store information about one check type
def _store_cached_checkinfo(hostname, checkname, table):
    info = _get_cached_hostinfo(hostname)
    if info:
        info[checkname] = table
    else:
        g_infocache[hostname] = { checkname: table }


#.
#   .--PersistedCache------------------------------------------------------.
#   |  ____               _     _           _  ____           _            |
#   | |  _ \ ___ _ __ ___(_)___| |_ ___  __| |/ ___|__ _  ___| |__   ___   |
#   | | |_) / _ \ '__/ __| / __| __/ _ \/ _` | |   / _` |/ __| '_ \ / _ \  |
#   | |  __/  __/ |  \__ \ \__ \ ||  __/ (_| | |__| (_| | (__| | | |  __/  |
#   | |_|   \___|_|  |___/_|___/\__\___|\__,_|\____\__,_|\___|_| |_|\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Caching of info for multiple executions of Check_MK. Mostly caching  |
#   | of sections that are not provided on each query.                     |
#   '----------------------------------------------------------------------'

def _store_persisted_info(hostname, persisted):
    dirname = cmk.paths.var_dir + "/persisted/"
    if persisted:
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        file_path = "%s/%s" % (dirname, hostname)
        store.save_data_to_file(file_path, persisted, pretty=False)

        console.verbose("Persisted sections %s.\n" % ", ".join(persisted.keys()))


def _add_persisted_info(hostname, info):
    # TODO: Use store.load_data_from_file
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

        if now < persisted_until or _enforce_persisting:
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
        _store_persisted_info(hostname, persisted)

#.
#   .--AgentCache----------------------------------------------------------.
#   |          _                    _    ____           _                  |
#   |         / \   __ _  ___ _ __ | |_ / ___|__ _  ___| |__   ___         |
#   |        / _ \ / _` |/ _ \ '_ \| __| |   / _` |/ __| '_ \ / _ \        |
#   |       / ___ \ (_| |  __/ | | | |_| |__| (_| | (__| | | |  __/        |
#   |      /_/   \_\__, |\___|_| |_|\__|\____\__,_|\___|_| |_|\___|        |
#   |              |___/                                                   |
#   +----------------------------------------------------------------------+
#   | This cache is used to prevent contacting remote systems too often.   |
#   | for example in cas of cluster monitoring.                            |
#   '----------------------------------------------------------------------'

def read_cache_file(relpath, max_cache_age):
    # Cache file present, caching allowed? -> read from cache
    # TODO: Use store.load_data_from_file
    cachefile = cmk.paths.tcp_cache_dir + "/" + relpath
    if os.path.exists(cachefile) and (
        (opt_use_cachefile and ( not _no_cache ) )
        or (config.simulation_mode and not _no_cache) ):
        if cmk_base.utils.cachefile_age(cachefile) <= max_cache_age or config.simulation_mode:
            result = open(cachefile).read()
            if result:
                console.verbose("Using data from cachefile %s.\n" % cachefile)
                return result
        else:
            console.vverbose("Skipping cache file %s: Too old "
                             "(age is %d sec, allowed is %s sec)\n" %
                             (cachefile, cmk_base.utils.cachefile_age(cachefile), max_cache_age))

    if config.simulation_mode and not _no_cache:
        raise MKAgentError("Simulation mode and no cachefile present.")

    if _no_tcp:
        raise MKAgentError("Host is unreachable, no usable cache file present")


def write_cache_file(relpath, output):
    cachefile = cmk.paths.tcp_cache_dir + "/" + relpath
    if not os.path.exists(cmk.paths.tcp_cache_dir):
        try:
            os.makedirs(cmk.paths.tcp_cache_dir)
        except Exception, e:
            raise MKGeneralException("Cannot create directory %s: %s" % (cmk.paths.tcp_cache_dir, e))
    try:
        f = open(cachefile, "w+")
        f.write(output)
        f.close()
    except Exception, e:
        raise MKGeneralException("Cannot write cache file %s: %s" % (cachefile, e))

#.
#   .--Agent---------------------------------------------------------------.
#   |                        _                    _                        |
#   |                       / \   __ _  ___ _ __ | |_                      |
#   |                      / _ \ / _` |/ _ \ '_ \| __|                     |
#   |                     / ___ \ (_| |  __/ | | | |_                      |
#   |                    /_/   \_\__, |\___|_| |_|\__|                     |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Real communication with the target system.                           |
#   '----------------------------------------------------------------------'

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

    if config.agent_simulator:
        output = cmk_base.agent_simulator.process(output)

    return output


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
        port = config.agent_port_of(hostname)

    encryption_settings = config.agent_encryption_of(hostname)

    try:
        s = socket.socket(config.is_ipv6_primary(hostname) and socket.AF_INET6 or socket.AF_INET,
                          socket.SOCK_STREAM)
        s.settimeout(config.tcp_connect_timeout)

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


#.
#   .--Datasoure Programs--------------------------------------------------.
#   |      ____        _                     ____                          |
#   |     |  _ \  __ _| |_ __ _ ___ _ __ ___|  _ \ _ __ ___   __ _         |
#   |     | | | |/ _` | __/ _` / __| '__/ __| |_) | '__/ _ \ / _` |        |
#   |     | |_| | (_| | || (_| \__ \ | | (__|  __/| | | (_) | (_| |_       |
#   |     |____/ \__,_|\__\__,_|___/_|  \___|_|   |_|  \___/ \__, (_)      |
#   |                                                        |___/         |
#   +----------------------------------------------------------------------+
#   | Fetching agent data from program calls instead of an agent           |
#   '----------------------------------------------------------------------'

def get_datasource_program(hostname, ipaddress):
    special_agents_dir       = cmk.paths.agents_dir + "/special"
    local_special_agents_dir = cmk.paths.local_agents_dir + "/special"

    # First check WATO-style special_agent rules
    for agentname, ruleset in config.special_agents.items():
        params = rulesets.host_extra_conf(hostname, ruleset)
        if params: # rule match!
            # Create command line using the special_agent_info
            cmd_arguments = checks.special_agent_info[agentname](params[0], hostname, ipaddress)
            if os.path.exists(local_special_agents_dir + "/agent_" + agentname):
                path = local_special_agents_dir + "/agent_" + agentname
            else:
                path = special_agents_dir + "/agent_" + agentname
            return _replace_datasource_program_macros(hostname, ipaddress,
                                                     path + " " + cmd_arguments)

    programs = rulesets.host_extra_conf(hostname, config.datasource_programs)
    if not programs:
        return None
    else:
        return _replace_datasource_program_macros(hostname, ipaddress, programs[0])


def _replace_datasource_program_macros(hostname, ipaddress, cmd):
    # Make "legacy" translation. The users should use the $...$ macros in future
    cmd = cmd.replace("<IP>", ipaddress).replace("<HOST>", hostname)

    tags = config.tags_of_host(hostname)
    attrs = core_config.get_host_attributes(hostname, tags)
    if config.is_cluster(hostname):
        parents_list = core_config.get_cluster_nodes_for_config(hostname)
        attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
        attrs.update(core_config.get_cluster_attributes(hostname, parents_list))

    macros = core_config.get_host_macros_from_attributes(hostname, attrs)
    return core_config.replace_macros(cmd, macros)


# Get data in case of external program
def get_agent_info_program(commandline):
    exepath = commandline.split()[0] # for error message, hide options!

    console.vverbose("Calling external program %s\n" % commandline)
    p = None
    try:
        if config.monitoring_core == "cmc":
            p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                 stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                 preexec_fn=os.setsid, close_fds=True)
        else:
            # We can not create a separate process group when running Nagios
            # Upon reaching the service_check_timeout Nagios only kills the process
            # group of the active check.
            p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                 stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                 close_fds=True)
        stdout, stderr = p.communicate()
        exitstatus = p.returncode
    except MKTimeout:
        # On timeout exception try to stop the process to prevent child process "leakage"
        if p:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            p.wait()
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

#.
#   .--Use cachefile-------------------------------------------------------.
#   |       _   _                           _           __ _ _             |
#   |      | | | |___  ___    ___ __ _  ___| |__   ___ / _(_) | ___        |
#   |      | | | / __|/ _ \  / __/ _` |/ __| '_ \ / _ \ |_| | |/ _ \       |
#   |      | |_| \__ \  __/ | (_| (_| | (__| | | |  __/  _| | |  __/       |
#   |       \___/|___/\___|  \___\__,_|\___|_| |_|\___|_| |_|_|\___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
# FIXME TODO: Cleanup the whole caching crap

opt_use_cachefile                = False
orig_opt_use_cachefile           = None
orig_check_max_cachefile_age     = None
orig_cluster_max_cachefile_age   = None
orig_inventory_max_cachefile_age = None

def get_use_cachefile():
    return opt_use_cachefile

def set_use_cachefile(state=True):
    global opt_use_cachefile, orig_opt_use_cachefile
    orig_opt_use_cachefile = opt_use_cachefile
    opt_use_cachefile = state


def restore_use_cachefile():
    global opt_use_cachefile, orig_opt_use_cachefile
    if orig_opt_use_cachefile != None:
        opt_use_cachefile = orig_opt_use_cachefile
        orig_opt_use_cachefile = None


# TODO: Why 1000000000? Can't we really clean this up to a global variable which can
# be toggled to enforce the cache usage (if available). This way we would not need
# to store the original values of the different caches and modify them etc.
def enforce_using_agent_cache():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if config.check_max_cachefile_age != 1000000000:
        orig_check_max_cachefile_age     = config.check_max_cachefile_age
        orig_cluster_max_cachefile_age   = config.cluster_max_cachefile_age
        orig_inventory_max_cachefile_age = config.inventory_max_cachefile_age

    config.check_max_cachefile_age     = 1000000000
    config.cluster_max_cachefile_age   = 1000000000
    config.inventory_max_cachefile_age = 1000000000


def restore_original_agent_caching_usage():
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if orig_check_max_cachefile_age != None:
        config.check_max_cachefile_age     = orig_check_max_cachefile_age
        config.cluster_max_cachefile_age   = orig_cluster_max_cachefile_age
        config.inventory_max_cachefile_age = orig_inventory_max_cachefile_age

        orig_check_max_cachefile_age     = None
        orig_cluster_max_cachefile_age   = None
        orig_inventory_max_cachefile_age = None


#.
#   .--Misc.---------------------------------------------------------------.
#   |                         __  __ _                                     |
#   |                        |  \/  (_)___  ___                            |
#   |                        | |\/| | / __|/ __|                           |
#   |                        | |  | | \__ \ (__ _                          |
#   |                        |_|  |_|_|___/\___(_)                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Different helper functions                                           |
#   '----------------------------------------------------------------------'

# TODO: Clean this up
def get_agent_cache_info():
    return g_agent_cache_info


def cleanup_host_caches():
    global g_agent_already_contacted
    g_agent_already_contacted = {}
    global g_infocache
    g_infocache = {}
    global g_agent_cache_info
    g_agent_cache_info = {}
    global g_broken_agent_hosts
    g_broken_agent_hosts = set()
    global g_broken_snmp_hosts
    g_broken_snmp_hosts = set()


def add_broken_agent_host(hostname):
    g_broken_agent_hosts.add(hostname)


def add_broken_snmp_host(hostname):
    g_broken_snmp_hosts.add(hostname)


def disable_agent_cache():
    global _no_cache
    _no_cache = True


def is_agent_cache_disabled():
    return _no_cache


def disable_tcp():
    global _no_tcp
    _no_tcp = True


def disable_submit():
    global _no_submit
    _no_submit = True


def enforce_persisting():
    global _enforce_persisting
    _enforce_persisting = True
