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

# Future convention within all Check_MK modules for variable names:
#
# - host_name     - Monitoring name of a host (string)
# - node_name     - Name of cluster member (string)
# - cluster_name  - Name of a cluster (string)
# - realhost_name - Name of a *real* host, not a cluster (string)

import os
import sys
import time
import pprint
import socket
import getopt
import re
import stat
import urllib
import subprocess
import fcntl
import py_compile
import inspect

from cStringIO import StringIO

from cmk.regex import regex, is_regex
from cmk.exceptions import MKGeneralException, MKTerminate, MKBailOut
import cmk.debug
import cmk.log
import cmk.tty as tty
import cmk.store as store
import cmk.paths
import cmk.render as render
import cmk.man_pages as man_pages
import cmk.password_store

import cmk_base
import cmk_base.console as console
import cmk_base.rulesets as rulesets
import cmk_base.checks as checks
import cmk_base.config as config
import cmk_base.default_config as default_config
import cmk_base.item_state as item_state
import cmk_base.piggyback as piggyback
import cmk_base.core_config as core_config
import cmk_base.ip_lookup as ip_lookup
import cmk_base.classic_snmp as classic_snmp
import cmk_base.snmp as snmp
from cmk_base.modes import modes
from cmk_base.exceptions import MKAgentError

# TODO: Clean up all calls and remove these aliases
tags_of_host    = config.tags_of_host
is_cluster      = config.is_cluster
nodes_of        = config.nodes_of

#   .--Prelude-------------------------------------------------------------.
#   |                  ____           _           _                        |
#   |                 |  _ \ _ __ ___| |_   _  __| | ___                   |
#   |                 | |_) | '__/ _ \ | | | |/ _` |/ _ \                  |
#   |                 |  __/| | |  __/ | |_| | (_| |  __/                  |
#   |                 |_|   |_|  \___|_|\__,_|\__,_|\___|                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Pre-Parsing of some command line options that are needed before     |
#   |  the main function.                                                  |
#   '----------------------------------------------------------------------'

# Some things have to be done before option parsing and might
# want to output some verbose messages.
g_profile      = None
g_profile_path = 'profile.out'

if '--debug' in sys.argv[1:]:
    cmk.debug.enable()

cmk.log.setup_console_logging()
logger = cmk.log.get_logger("base")

# TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
#       The later regular argument parsing is handling this correctly. Try to clean this up.
cmk.log.set_verbosity(verbosity=len([ a for a in sys.argv if a in [ "-v", "--verbose"] ]))

if '--profile' in sys.argv[1:]:
    import cProfile
    g_profile = cProfile.Profile()
    g_profile.enable()
    console.verbose("Enabled profiling.\n")


#.
#   .--Pathnames-----------------------------------------------------------.
#   |        ____       _   _                                              |
#   |       |  _ \ __ _| |_| |__  _ __   __ _ _ __ ___   ___  ___          |
#   |       | |_) / _` | __| '_ \| '_ \ / _` | '_ ` _ \ / _ \/ __|         |
#   |       |  __/ (_| | |_| | | | | | | (_| | | | | | |  __/\__ \         |
#   |       |_|   \__,_|\__|_| |_|_| |_|\__,_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO: Can this be cleaned up? Can we drop the "-c" option? Otherwise: move it to cmk.paths?
#
# Now determine the location of the directory containing main.mk. It
# is searched for at several places:
#
# 1. if present - the option '-c' specifies the path to main.mk
# 2. in the default_config_dir (that path should be present in modules/defaults)

try:
    i = sys.argv.index('-c')
    if i > 0 and i < len(sys.argv)-1:
        cmk.paths.main_config_file = sys.argv[i+1]
        parts = cmk.paths.main_config_file.split('/')
        if len(parts) > 1:
            check_mk_basedir = cmk.paths.main_config_file.rsplit('/',1)[0]
        else:
            check_mk_basedir = "." # no / contained in filename

        if not os.path.exists(check_mk_basedir):
            sys.stderr.write("Directory %s does not exist.\n" % check_mk_basedir)
            sys.exit(1)

        if not os.path.exists(cmk.paths.main_config_file):
            sys.stderr.write("Missing configuration file %s.\n" % cmk.paths.main_config_file)
            sys.exit(1)

        # Also rewrite the location of the conf.d directory
        if os.path.exists(check_mk_basedir + "/conf.d"):
            cmk.paths.check_mk_config_dir = check_mk_basedir + "/conf.d"

    else:
        sys.stderr.write("Missing argument to option -c.\n")
        sys.exit(1)

except ValueError:
    cmk.paths.main_config_file = cmk.paths.default_config_dir + "/main.mk"
    if not os.path.exists(cmk.paths.main_config_file):
        sys.stderr.write("Missing main configuration file %s\n" % cmk.paths.main_config_file)
        sys.exit(4)

except SystemExit, exitcode:
    sys.exit(exitcode)


#.
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some constants to be used in the configuration and at other places   |
#   '----------------------------------------------------------------------'

# Conveniance macros for host and service rules
# TODO: Cleanup when not needed anymore in modules
PHYSICAL_HOSTS = rulesets.PHYSICAL_HOSTS
CLUSTER_HOSTS  = rulesets.CLUSTER_HOSTS
ALL_HOSTS      = rulesets.ALL_HOSTS
ALL_SERVICES   = rulesets.ALL_SERVICES
NEGATE         = rulesets.NEGATE

# Renaming of service descriptions while keeping backward compatibility with
# existing installations.
# Synchronize with htdocs/wato.py and plugins/wato/check_mk_configuration.py!

# Cleanup! .. some day
def get_old_cmciii_temp_description(item):
    if "Temperature" in item:
        return False, item # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return False, "%s Temperature" % parts[1]

    elif len(parts) == 2:
        return False, "%s %s.Temperature" % (parts[1], parts[0])

    else:
        if parts[1] == "LCP":
            parts[1] = "Liquid_Cooling_Package"
        return False, "%s %s.%s-Temperature" % (parts[1], parts[0], parts[2])

old_service_descriptions = {
    "df"                               : "fs_%s",
    "df_netapp"                        : "fs_%s",
    "df_netapp32"                      : "fs_%s",
    "esx_vsphere_datastores"           : "fs_%s",
    "hr_fs"                            : "fs_%s",
    "vms_diskstat.df"                  : "fs_%s",
    "zfsget"                           : "fs_%s",
    "ps"                               : "proc_%s",
    "ps.perf"                          : "proc_%s",
    "wmic_process"                     : "proc_%s",
    "services"                         : "service_%s",
    "logwatch"                         : "LOG %s",
    "logwatch.groups"                  : "LOG %s",
    "hyperv_vm"                        : "hyperv_vms",
    "ibm_svc_mdiskgrp"                 : "MDiskGrp %s",
    "ibm_svc_system"                   : "IBM SVC Info",
    "ibm_svc_systemstats.diskio"       : "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats.iops"         : "IBM SVC IOPS %s Total",
    "ibm_svc_systemstats.disk_latency" : "IBM SVC Latency %s Total",
    "ibm_svc_systemstats.cache"        : "IBM SVC Cache Total",
    "mknotifyd"                        : "Notification Spooler %s",
    "mknotifyd.connection"             : "Notification Connection %s",

    "casa_cpu_temp"                    : "Temperature %s",
    "cmciii.temp"                      : get_old_cmciii_temp_description,
    "cmciii.psm_current"               : "%s",
    "cmciii_lcp_airin"                 : "LCP Fanunit Air IN",
    "cmciii_lcp_airout"                : "LCP Fanunit Air OUT",
    "cmciii_lcp_water"                 : "LCP Fanunit Water %s",
    "etherbox.temp"                    : "Sensor %s",
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "liebert_bat_temp"                 : lambda item: (False, "Battery Temp"),
    "nvidia.temp"                      : "Temperature NVIDIA %s",
    "ups_bat_temp"                     : "Temperature Battery %s",
    "innovaphone_temp"                 : lambda item: (False, "Temperature"),
    "enterasys_temp"                   : lambda item: (False, "Temperature"),
    "raritan_emx"                      : "Rack %s",
    "raritan_pdu_inlet"                : "Input Phase %s",
    "postfix_mailq"                    : lambda item: (False, "Postfix Queue"),
    "nullmailer_mailq"                 : lambda item: (False, "Nullmailer Queue"),
    "barracuda_mailqueues"             : lambda item: (False, "Mail Queue"),
    "qmail_stats"                      : lambda item: (False, "Qmail Queue"),
}

# workaround: set of check-groups that are to be treated as service-checks even if
#   the item is None
service_rule_groups = set([
    "temperature"
])


#.
#   .--Modules-------------------------------------------------------------.
#   |                __  __           _       _                            |
#   |               |  \/  | ___   __| |_   _| | ___  ___                  |
#   |               | |\/| |/ _ \ / _` | | | | |/ _ \/ __|                 |
#   |               | |  | | (_) | (_| | |_| | |  __/\__ \                 |
#   |               |_|  |_|\___/ \__,_|\__,_|_|\___||___/                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Load the other modules                                              |
#   '----------------------------------------------------------------------'

def module_exists(name):
    path = cmk.paths.modules_dir + "/" + name + ".py"
    return os.path.exists(path)

def load_module(name):
    path = cmk.paths.modules_dir + "/" + name + ".py"
    execfile(path, globals())


# at check time (and many of what is also needed at administration time).
try:
    modules = [ 'check_mk_base', 'discovery', 'notify', 'events',
                'alert_handling', 'cmc', 'agent_bakery', 'managed' ]
    for module in modules:
        if module_exists(module):
            load_module(module)

except Exception, e:
    if cmk.debug.enabled():
        raise
    sys.stderr.write("Cannot read module %s: %s\n" % (module, e))
    sys.exit(5)


#.

#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with hosts.                            |
#   '----------------------------------------------------------------------'
# TODO: Move to config.

def parse_hostname_list(args, with_clusters = True, with_foreign_hosts = False):
    if with_foreign_hosts:
        valid_hosts = config.all_configured_realhosts()
    else:
        valid_hosts = config.all_active_realhosts()

    if with_clusters:
        valid_hosts = valid_hosts.union(config.all_active_clusters())

    hostlist = []
    for arg in args:
        if arg[0] != '@' and arg in valid_hosts:
            hostlist.append(arg)
        else:
            if arg[0] == '@':
                arg = arg[1:]
            tagspec = arg.split(',')

            num_found = 0
            for hostname in valid_hosts:
                if rulesets.hosttags_match_taglist(tags_of_host(hostname), tagspec):
                    hostlist.append(hostname)
                    num_found += 1
            if num_found == 0:
                sys.stderr.write("Hostname or tag specification '%s' does "
                                 "not match any host.\n" % arg)
                sys.exit(1)
    return hostlist


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Misc functions which do not belong to any other topic                |
#   '----------------------------------------------------------------------'

# FIXME TODO: Cleanup the whole caching crap
orig_opt_use_cachefile           = None
orig_check_max_cachefile_age     = None
orig_cluster_max_cachefile_age   = None
orig_inventory_max_cachefile_age = None


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


def schedule_inventory_check(hostname):
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(cmk.paths.livestatus_unix_socket)
        now = int(time.time())
        if 'cmk-inventory' in config.use_new_descriptions_for:
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK Discovery;%d" % (hostname, now)
        else:
            # TODO: Remove this old name handling one day
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK inventory;%d" % (hostname, now)

        # Ignore missing check and avoid warning in cmc.log
        if config.monitoring_core == "cmc":
            command += ";TRY"

        s.send("COMMAND [%d] %s\n" % (now, command))
    except Exception:
        if cmk.debug.enabled():
            raise

#.
#   .--Checktable----------------------------------------------------------.
#   |           ____ _               _    _        _     _                 |
#   |          / ___| |__   ___  ___| | _| |_ __ _| |__ | | ___            |
#   |         | |   | '_ \ / _ \/ __| |/ / __/ _` | '_ \| |/ _ \           |
#   |         | |___| | | |  __/ (__|   <| || (_| | |_) | |  __/           |
#   |          \____|_| |_|\___|\___|_|\_\\__\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Code for computing the table of checks of a host.                    |
#   '----------------------------------------------------------------------'

# Returns check table for a specific host
# Format: (checkname, item) -> (params, description)

def get_check_table(hostname, remove_duplicates=False, use_cache=True, world='config', skip_autochecks=False):

    if config.is_ping_host(hostname):
        skip_autochecks = True

    # speed up multiple lookup of same host
    check_table_cache = cmk_base.config_cache.get_dict("check_tables")
    if not skip_autochecks and use_cache and hostname in check_table_cache:
        if remove_duplicates and config.is_dual_host(hostname):
            return remove_duplicate_checks(check_table_cache[hostname])
        else:
            return check_table_cache[hostname]

    check_table = {}

    single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")
    multi_host_checks  = cmk_base.config_cache.get_list("multi_host_checks")

    hosttags = tags_of_host(hostname)

    # Just a local cache and its function
    is_checkname_valid_cache = {}
    def is_checkname_valid(checkname):
        the_id = (hostname, checkname)
        if the_id in is_checkname_valid_cache:
            return is_checkname_valid_cache[the_id]

        passed = True
        # Skip SNMP checks for non SNMP hosts (might have been discovered before with other
        # agent setting. Remove them without rediscovery). Same for agent based checks.
        if not config.is_snmp_host(hostname) and checks.is_snmp_check(checkname) and \
           (not config.has_management_board(hostname) or config.management_protocol(hostname) != "snmp"):
                passed = False
        if not config.is_tcp_host(hostname) and not piggyback.has_piggyback_info(hostname) \
           and checks.is_tcp_check(checkname):
            passed = False
        is_checkname_valid_cache[the_id] = passed
        return passed


    def handle_entry(entry):
        num_elements = len(entry)
        if num_elements == 3: # from autochecks
            hostlist = hostname
            checkname, item, params = entry
            tags = []
        elif num_elements == 4:
            hostlist, checkname, item, params = entry
            tags = []
        elif num_elements == 5:
            tags, hostlist, checkname, item, params = entry
            if type(tags) != list:
                raise MKGeneralException("Invalid entry '%r' in check table. First entry must be list of host tags." %
                                         (entry, ))

        else:
            raise MKGeneralException("Invalid entry '%r' in check table. It has %d entries, but must have 4 or 5." %
                                     (entry, len(entry)))

        # hostlist list might be:
        # 1. a plain hostname (string)
        # 2. a list of hostnames (list of strings)
        # Hostnames may be tagged. Tags are removed.
        # In autochecks there are always single untagged hostnames. We optimize for that.
        if type(hostlist) == str:
            if hostlist != hostname:
                return # optimize most common case: hostname mismatch
            hostlist = [ hostlist ]
        elif type(hostlist[0]) == str:
            pass # regular case: list of hostnames
        elif hostlist != []:
            raise MKGeneralException("Invalid entry '%r' in check table. Must be single hostname "
                                     "or list of hostnames" % hostlist)


        if not is_checkname_valid(checkname):
            return

        if rulesets.hosttags_match_taglist(hosttags, tags) and \
               rulesets.in_extraconf_hostlist(hostlist, hostname):
            descr = service_description(hostname, checkname, item)
            if service_ignored(hostname, checkname, descr):
                return
            if hostname != config.host_of_clustered_service(hostname, descr):
                return
            deps  = service_deps(hostname, descr)
            check_table[(checkname, item)] = (params, descr, deps)

    # Now process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not skip_autochecks:
        for entry in read_autochecks_of(hostname, world):
            handle_entry(entry)

    for entry in single_host_checks.get(hostname, []):
        handle_entry(entry)

    for entry in multi_host_checks:
        handle_entry(entry)

    # Now add checks a cluster might receive from its nodes
    if is_cluster(hostname):
        single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")

        for node in nodes_of(hostname):
            node_checks = single_host_checks.get(node, [])
            if not skip_autochecks:
                node_checks = node_checks + read_autochecks_of(node, world)
            for entry in node_checks:
                if len(entry) == 4:
                    entry = entry[1:] # drop hostname from single_host_checks
                checkname, item, params = entry
                descr = service_description(node, checkname, item)
                if hostname == config.host_of_clustered_service(node, descr):
                    cluster_params = compute_check_parameters(hostname, checkname, item, params)
                    handle_entry((hostname, checkname, item, cluster_params))


    # Remove dependencies to non-existing services
    all_descr = set([ descr for ((checkname, item), (params, descr, deps)) in check_table.items() ])
    for (checkname, item), (params, descr, deps) in check_table.items():
        deeps = deps[:]
        del deps[:]
        for d in deeps:
            if d in all_descr:
                deps.append(d)

    if not skip_autochecks and use_cache:
        check_table_cache[hostname] = check_table

    if remove_duplicates:
        return remove_duplicate_checks(check_table)
    else:
        return check_table


def get_precompiled_check_table(hostname, remove_duplicates=True, world="config"):
    host_checks = get_sorted_check_table(hostname, remove_duplicates, world)
    precomp_table = []
    for check_type, item, params, description, _unused_deps in host_checks:
        # make these globals available to the precompile function
        checks.set_service_description(description)
        item_state.set_item_state_prefix(check_type, item)

        params = get_precompiled_check_parameters(hostname, item, params, check_type)
        precomp_table.append((check_type, item, params, description)) # deps not needed while checking
    return precomp_table


def get_precompiled_check_parameters(hostname, item, params, check_type):
    precomp_func = checks.precompile_params.get(check_type)
    if precomp_func:
        return precomp_func(hostname, item, params)
    else:
        return params


# Return a list of services this services depends upon
# TODO: Make this use the generic "rulesets" functions
def service_deps(hostname, servicedesc):
    deps = []
    for entry in config.service_dependencies:
        entry, rule_options = rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags = []
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service dependencies: "
                                     "must have 3 or 4 entries" % entry)

        if rulesets.hosttags_match_taglist(tags_of_host(hostname), tags) and \
           rulesets.in_extraconf_hostlist(hostlist, hostname):
            for pattern in patternlist:
                matchobject = regex(pattern).search(servicedesc)
                if matchobject:
                    try:
                        item = matchobject.groups()[-1]
                        deps.append(depname % item)
                    except:
                        deps.append(depname)
    return deps



def remove_duplicate_checks(check_table):
    have_with_tcp = {}
    have_with_snmp = {}
    without_duplicates = {}
    for key, value in check_table.iteritems():
        checkname = key[0]
        descr = value[1]
        if checks.is_snmp_check(checkname):
            if descr in have_with_tcp:
                continue
            have_with_snmp[descr] = key
        else:
            if descr in have_with_snmp:
                snmp_key = have_with_snmp[descr]
                del without_duplicates[snmp_key]
                del have_with_snmp[descr]
            have_with_tcp[descr] = key
        without_duplicates[key] = value
    return without_duplicates



# remove_duplicates: Automatically remove SNMP based checks
# if there already is a TCP based one with the same
# description. E.g: df vs hr_fs.
def get_sorted_check_table(hostname, remove_duplicates=False, world="config"):
    # Convert from dictionary into simple tuple list. Then sort
    # it according to the service dependencies.
    unsorted = [ (checkname, item, params, descr, deps)
                 for ((checkname, item), (params, descr, deps))
                 in get_check_table(hostname, remove_duplicates=remove_duplicates, world=world).items() ]
    def cmp(a, b):
        if a[3] < b[3]:
            return -1
        else:
            return 1
    unsorted.sort(cmp)


    sorted = []
    while len(unsorted) > 0:
        unsorted_descrs = set([ entry[3] for entry in unsorted ])
        left = []
        at_least_one_hit = False
        for check in unsorted:
            deps_fulfilled = True
            for dep in check[4]: # deps
                if dep in unsorted_descrs:
                    deps_fulfilled = False
                    break
            if deps_fulfilled:
                sorted.append(check)
                at_least_one_hit = True
            else:
                left.append(check)
        if len(left) == 0:
            break
        if not at_least_one_hit:
            raise MKGeneralException("Cyclic service dependency of host %s. Problematic are: %s" %
                                     (hostname, ",".join(unsorted_descrs)))
        unsorted = left
    return sorted



# Determine, which program to call to get the agent data. This is an alternative to fetch
# the agent data via TCP port, mostly used for special agents.
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
            return replace_datasource_program_macros(hostname, ipaddress,
                                                     path + " " + cmd_arguments)


    programs = rulesets.host_extra_conf(hostname, config.datasource_programs)
    if not programs:
        return None
    else:
        return replace_datasource_program_macros(hostname, ipaddress, programs[0])


def replace_datasource_program_macros(hostname, ipaddress, cmd):
    # Make "legacy" translation. The users should use the $...$ macros in future
    cmd = cmd.replace("<IP>", ipaddress).replace("<HOST>", hostname)

    tags = tags_of_host(hostname)
    attrs = get_host_attributes(hostname, tags)
    if is_cluster(hostname):
        parents_list = get_cluster_nodes_for_config(hostname)
        attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
        attrs.update(get_cluster_attributes(hostname, parents_list))

    macros = get_host_macros_from_attributes(hostname, attrs)
    return replace_macros(cmd, macros)


def service_description(hostname, check_type, item):
    if check_type not in checks.check_info:
        if item:
            return "Unimplemented check %s / %s" % (check_type, item)
        else:
            return "Unimplemented check %s" % check_type

    # use user-supplied service description, if available
    add_item = True
    descr_format = config.service_descriptions.get(check_type)
    if not descr_format:
        # handle renaming for backward compatibility
        if check_type in old_service_descriptions and \
            check_type not in config.use_new_descriptions_for:

            # Can be a fucntion to generate the old description more flexible.
            old_descr = old_service_descriptions[check_type]
            if callable(old_descr):
                add_item, descr_format = old_descr(item)
            else:
                descr_format = old_descr

        else:
            descr_format = checks.check_info[check_type]["service_description"]

    if type(descr_format) == str:
        descr_format = descr_format.decode("utf-8")

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.

    item_type = type(item)
    if add_item and item_type in [ str, unicode, int, long ]:
        # Remove characters from item name that are banned by Nagios
        if item_type in [ str, unicode ]:
            item_safe = checks.sanitize_service_description(item)
        else:
            item_safe = str(item)

        if "%s" not in descr_format:
            descr_format += " %s"

        descr = descr_format % (item_safe,)
    else:
        descr = descr_format

    if "%s" in descr:
        raise MKGeneralException("Found '%%s' in service description (Host: %s, Check type: %s, Item: %s). "
                                 "Please try to rediscover the service to fix this issue." % (hostname, check_type, item))

    return descr.strip()


#.
#   .--Pack config---------------------------------------------------------.
#   |         ____            _                       __ _                 |
#   |        |  _ \ __ _  ___| | __   ___ ___  _ __  / _(_) __ _           |
#   |        | |_) / _` |/ __| |/ /  / __/ _ \| '_ \| |_| |/ _` |          |
#   |        |  __/ (_| | (__|   <  | (_| (_) | | | |  _| | (_| |          |
#   |        |_|   \__,_|\___|_|\_\  \___\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   |  Create packaged and precompiled config for keepalive mode           |
#   '----------------------------------------------------------------------'

# Create a packed version of the configuration (main.mk and friend)
# and put that to var/check_mk/core/config.mk. Also create a copy
# of all autochecks files. The check helpers of the running core just
# use those files, so that changes in the actual config do not harm
# the running system.

# Make service levels available during check execution
derived_config_variable_names = [ "service_service_levels", "host_service_levels" ]

# These variables are part of the Check_MK configuration, but are not needed
# by the Check_MK keepalive mode, so exclude them from the packed config
skipped_config_variable_names = [
    "define_contactgroups",
    "define_hostgroups",
    "define_servicegroups",
    "service_contactgroups",
    "host_contactgroups",
    "service_groups",
    "host_groups",
    "contacts",
    "host_paths",
    "timeperiods",
    "extra_service_conf",
    "extra_host_conf",
    "extra_nagios_conf",
]

def pack_config():
    # Checks whether or not a variable can be written to the config.mk
    # and read again from it.
    def packable(varname, val):
        if type(val) in [ int, str, unicode, bool ] or not val:
            return True

        try:
            eval(repr(val))
            return True
        except:
            return False

    helper_config = (
        "#!/usr/bin/python\n"
        "# encoding: utf-8\n"
        "# Created by Check_MK. Dump of the currently active configuration\n\n"
    )

    # These functions purpose is to filter out hosts which are monitored on different sites
    active_hosts    = config.all_active_hosts()
    active_clusters = config.all_active_clusters()
    def filter_all_hosts(all_hosts):
        all_hosts_red = []
        for host_entry in all_hosts:
            hostname = host_entry.split("|", 1)[0]
            if hostname in active_hosts:
                all_hosts_red.append(host_entry)
        return all_hosts_red

    def filter_clusters(clusters):
        clusters_red = {}
        for cluster_entry, cluster_nodes in clusters.items():
            clustername = cluster_entry.split("|", 1)[0]
            if clustername in active_clusters:
                clusters_red[cluster_entry] = cluster_nodes
        return clusters_red

    def filter_hostname_in_dict(values):
        values_red = {}
        for hostname, attributes in values.items():
            if hostname in active_hosts:
                values_red[hostname] = attributes
        return values_red

    filter_var_functions = {
        "all_hosts"                : filter_all_hosts,
        "clusters"                 : filter_clusters,
        "host_attributes"          : filter_hostname_in_dict,
        "ipaddresses"              : filter_hostname_in_dict,
        "ipv6addresses"            : filter_hostname_in_dict,
        "explicit_snmp_communities": filter_hostname_in_dict,
        "hosttags"                 : filter_hostname_in_dict
    }

    for varname in config.get_variable_names() + derived_config_variable_names:
        if varname not in skipped_config_variable_names:
            val = getattr(config, varname)
            if packable(varname, val):
                if varname in filter_var_functions:
                    val = filter_var_functions[varname](val)
                helper_config += "\n%s = %r\n" % (varname, val)

    for varname, _unused_factory_setting in checks.factory_settings.items():
        if hasattr(config, varname):
            helper_config += "\n%s = %r\n" % (varname, getattr(config, varname))
        else: # remove explicit setting from previous packed config!
            helper_config += "\nif %r in globals():\n    del %s\n" % (varname, varname)


    filepath = cmk.paths.var_dir + "/core/helper_config.mk"

    file(filepath + ".orig", "w").write(helper_config)

    import marshal
    code = compile(helper_config, '<string>', 'exec')
    with open(filepath + ".compiled", "w") as compiled_file:
        marshal.dump(code, compiled_file)

    os.rename(filepath + ".compiled", filepath)


def pack_autochecks():
    dstpath = cmk.paths.var_dir + "/core/autochecks"
    if not os.path.exists(dstpath):
        os.makedirs(dstpath)
    srcpath = cmk.paths.autochecks_dir
    needed = set([])

    # hardlink used files
    for f in os.listdir(srcpath):
        if f.endswith(".mk"):
            d = dstpath + "/" + f
            if os.path.exists(d):
                os.remove(d)
            os.link(srcpath + "/" + f, d)
            needed.add(f)

    # Remove obsolete files
    for f in os.listdir(dstpath):
        if f not in needed:
            os.remove(dstpath + "/" + f)


def do_flush(hosts):
    if not hosts:
        hosts = config.all_active_hosts()
    for host in hosts:
        sys.stdout.write("%-20s: " % host)
        sys.stdout.flush()
        flushed = False

        # counters
        try:
            os.remove(cmk.paths.counters_dir + "/" + host)
            sys.stdout.write(tty.bold + tty.blue + " counters")
            sys.stdout.flush()
            flushed = True
        except:
            pass

        # cache files
        d = 0
        dir = cmk.paths.tcp_cache_dir
        if os.path.exists(dir):
            for f in os.listdir(dir):
                if f == host or f.startswith(host + "."):
                    try:
                        os.remove(dir + "/" + f)
                        d += 1
                        flushed = True
                    except:
                        pass
            if d == 1:
                sys.stdout.write(tty.bold + tty.green + " cache")
            elif d > 1:
                sys.stdout.write(tty.bold + tty.green + " cache(%d)" % d)
            sys.stdout.flush()

        # piggy files from this as source host
        d = piggyback.remove_piggyback_info_from(host)
        if d:
            sys.stdout.write(tty.bold + tty.magenta  + " piggyback(%d)" % d)


        # logfiles
        dir = cmk.paths.logwatch_dir + "/" + host
        if os.path.exists(dir):
            d = 0
            for f in os.listdir(dir):
                if f not in [".", ".."]:
                    try:
                        os.remove(dir + "/" + f)
                        d += 1
                        flushed = True
                    except:
                        pass
            if d > 0:
                sys.stdout.write(tty.bold + tty.magenta + " logfiles(%d)" % d)

        # autochecks
        count = remove_autochecks_of(host)
        if count:
            flushed = True
            sys.stdout.write(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        path = cmk.paths.var_dir + "/inventory/" + host
        if os.path.exists(path):
            os.remove(path)
            sys.stdout.write(tty.bold + tty.yellow + " inventory")

        if not flushed:
            sys.stdout.write("(nothing)")

        sys.stdout.write(tty.normal + "\n")


#.
#   .--Core Config---------------------------------------------------------.
#   |          ____                  ____             __ _                 |
#   |         / ___|___  _ __ ___   / ___|___  _ __  / _(_) __ _           |
#   |        | |   / _ \| '__/ _ \ | |   / _ \| '_ \| |_| |/ _` |          |
#   |        | |__| (_) | | |  __/ | |__| (_) | | | |  _| | (_| |          |
#   |         \____\___/|_|  \___|  \____\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   | Code for managing the core configuration creation.                   |
#   '----------------------------------------------------------------------'
# TODO: Move to cmk_base.core_config

def create_core_config():
    core_config.initialize_warnings()

    verify_non_duplicate_hosts()
    verify_non_deprecated_checkgroups()

    if config.monitoring_core == "cmc":
        do_create_cmc_config(opt_cmc_relfilename)
    else:
        load_module("nagios")
        out = file(cmk.paths.nagios_objects_file, "w")
        create_nagios_config(out)

    cmk.password_store.save(stored_passwords)

    return core_config.get_configuration_warnings()


# Verify that the user has no deprecated check groups configured.
def verify_non_deprecated_checkgroups():
    groups = checks.checks_by_checkgroup()

    for checkgroup in config.checkgroup_parameters.keys():
        if checkgroup not in groups:
            core_config.warning(
                "Found configured rules of deprecated check group \"%s\". These rules are not used "
                "by any check. Maybe this check group has been renamed during an update, "
                "in this case you will have to migrate your configuration to the new ruleset manually. "
                "Please check out the release notes of the involved versions. "
                "You may use the page \"Deprecated rules\" in WATO to view your rules and move them to "
                "the new rulesets." % checkgroup)


def verify_non_duplicate_hosts():
    duplicates = config.duplicate_hosts()
    if duplicates:
        core_config.warning(
              "The following host names have duplicates: %s. "
              "This might lead to invalid/incomplete monitoring for these hosts." % ", ".join(duplicates))


def verify_cluster_address_family(hostname):
    cluster_host_family = config.is_ipv6_primary(hostname) and "IPv6" or "IPv4"

    address_families = [
        "%s: %s" % (hostname, cluster_host_family),
    ]

    address_family = cluster_host_family
    mixed = False
    for nodename in nodes_of(hostname):
        family = config.is_ipv6_primary(nodename) and "IPv6" or "IPv4"
        address_families.append("%s: %s" % (nodename, family))
        if address_family == None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        core_config.warning("Cluster '%s' has different primary address families: %s" %
                                                         (hostname, ", ".join(address_families)))


def get_cluster_nodes_for_config(hostname):
    verify_cluster_address_family(hostname)

    nodes = nodes_of(hostname)[:]
    for node in nodes:
        if node not in config.all_active_realhosts():
            core_config.warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
                                                                                      (node, hostname))
            nodes.remove(node)
    return nodes


def get_host_macros_from_attributes(hostname, attrs):
    macros = {
        "$HOSTNAME$"    : hostname,
        "$HOSTADDRESS$" : attrs['address'],
        "$HOSTALIAS$"   : attrs['alias'],
    }

    # Add custom macros
    for macro_name, value in attrs.items():
        if macro_name[0] == '_':
            macros["$HOST" + macro_name + "$"] = value
            # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
            macros["$_HOST" + macro_name[1:] + "$"] = value

    return macros


def get_host_attributes(hostname, tags):
    attrs = extra_host_attributes(hostname)

    attrs["_TAGS"] = " ".join(tags)

    if "alias" not in attrs:
        attrs["alias"] = config.alias_of(hostname, hostname)

    # Now lookup configured IP addresses
    if config.is_ipv4_host(hostname):
        attrs["_ADDRESS_4"] = ip_address_of(hostname, 4)
        if attrs["_ADDRESS_4"] == None:
            attrs["_ADDRESS_4"] = ""
    else:
        attrs["_ADDRESS_4"] = ""

    if config.is_ipv6_host(hostname):
        attrs["_ADDRESS_6"] = ip_address_of(hostname, 6)
        if attrs["_ADDRESS_6"] == None:
            attrs["_ADDRESS_6"] = ""
    else:
        attrs["_ADDRESS_6"] = ""

    ipv6_primary = config.is_ipv6_primary(hostname)
    if ipv6_primary:
        attrs["address"]        = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"]        = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    # Add the optional WATO folder path
    path = config.host_paths.get(hostname)
    if path:
        attrs["_FILENAME"] = path

    # Add custom user icons and actions
    actions = core_config.icons_and_actions_of("host", hostname)
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)

    if cmk.is_managed_edition():
        attrs["_CUSTOMER"] = current_customer

    return attrs


def extra_host_attributes(hostname):
    attrs = {}
    for key, conflist in config.extra_host_conf.items():
        values = rulesets.host_extra_conf(hostname, conflist)
        if values:
            if key[0] == "_":
                key = key.upper()

            if values[0] != None:
                attrs[key] = values[0]
    return attrs


def get_cluster_attributes(hostname, nodes):
    attrs = {}
    node_ips_4 = []
    if config.is_ipv4_host(hostname):
        for h in nodes:
            addr = ip_address_of(h, 4)
            if addr != None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(fallback_ip_for(hostname, 4))

    node_ips_6 = []
    if config.is_ipv6_host(hostname):
        for h in nodes:
            addr = ip_address_of(h, 6)
            if addr != None:
                node_ips_6.append(addr)
            else:
                node_ips_6.append(fallback_ip_for(hostname, 6))

    if config.is_ipv6_primary(hostname):
        node_ips = node_ips_6
    else:
        node_ips = node_ips_4

    for suffix, val in [ ("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6) ]:
        attrs["_NODEIPS%s" % suffix] = " ".join(val)

    return attrs


ignore_ip_lookup_failures = False
g_failed_ip_lookups = []

def ip_address_of(hostname, family=None):
    try:
        return ip_lookup.lookup_ip_address(hostname, family)
    except Exception, e:
        if is_cluster(hostname):
            return ""
        else:
            g_failed_ip_lookups.append(hostname)
            if not ignore_ip_lookup_failures:
                core_config.warning("Cannot lookup IP address of '%s' (%s). "
                                      "The host will not be monitored correctly." % (hostname, e))
            return fallback_ip_for(hostname, family)


def fallback_ip_for(hostname, family=None):
    if family == None:
        family = config.is_ipv6_primary(hostname) and 6 or 4

    if family == 4:
        return "0.0.0.0"
    else:
        return "::"

def replace_macros(s, macros):
    for key, value in macros.items():
        if type(value) in (int, long, float):
            value = str(value) # e.g. in _EC_SL (service level)

        # TODO: Clean this up
        try:
            s = s.replace(key, value)
        except: # Might have failed due to binary UTF-8 encoding in value
            try:
                s = s.replace(key, value.decode("utf-8"))
            except:
                # If this does not help, do not replace
                if cmk.debug.enabled():
                    raise

    return s


#.
#   .--Main Functions------------------------------------------------------.
#   | __  __       _         _____                 _   _                   |
#   ||  \/  | __ _(_)_ __   |  ___|   _ _ __   ___| |_(_) ___  _ __  ___   |
#   || |\/| |/ _` | | '_ \  | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|  |
#   || |  | | (_| | | | | | |  _|| |_| | | | | (__| |_| | (_) | | | \__ \  |
#   ||_|  |_|\__,_|_|_| |_| |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Implementation of some of the toplevel functions.                    |
#   '----------------------------------------------------------------------'

def get_plain_hostinfo(hostname):
    info = read_cache_file(hostname, 999999999)
    if info:
        return info
    else:
        info = ""
        if config.is_tcp_host(hostname):
            ipaddress = ip_lookup.lookup_ip_address(hostname)
            info += get_agent_info(hostname, ipaddress, 0)
        info += piggyback.get_piggyback_info(hostname)
        return info


# Implementation of option -d
def output_plain_hostinfo(hostname):
    try:
        sys.stdout.write(get_plain_hostinfo(hostname))
    except MKAgentError, e:
        sys.stderr.write("Problem contacting agent: %s\n" % (e,))
        sys.exit(3)
    except MKGeneralException, e:
        sys.stderr.write("General problem: %s\n" % (e,))
        sys.exit(3)
    except socket.gaierror, e:
        sys.stderr.write("Network error: %s\n" % e)
    except Exception, e:
        sys.stderr.write("Unhandled exception: %s\n" % (e,))
        sys.exit(3)


def do_snmptranslate(args):
    if not args:
        raise MKGeneralException("Please provide the name of a SNMP walk file")
    walk_filename = args[0]

    walk_path = "%s/%s" % (cmk.paths.snmpwalks_dir, walk_filename)
    if not os.path.exists(walk_path):
        raise MKGeneralException("Walk does not exist")

    def translate(lines):
        result_lines = []
        try:
            oids_for_command = []
            for line in lines:
                oids_for_command.append(line.split(" ")[0])

            command = "snmptranslate -m ALL -M+%s %s 2>/dev/null" % \
                        (cmk.paths.local_mibs_dir, " ".join(oids_for_command))
            process = os.popen(command, "r")
            output  = process.read()
            result  = output.split("\n")[0::2]
            for idx, line in enumerate(result):
                result_lines.append((line.strip(), lines[idx].strip()))

        except Exception, e:
            sys.stdout.write("%s\n" % e)

        return result_lines


    # Translate n-oid's per cycle
    entries_per_cycle = 500
    translated_lines = []

    walk_lines = file(walk_path).readlines()
    sys.stderr.write("Processing %d lines.\n" %  len(walk_lines))

    i = 0
    while i < len(walk_lines):
        sys.stderr.write("\r%d to go...    " % (len(walk_lines) - i))
        sys.stderr.flush()
        process_lines = walk_lines[i:i+entries_per_cycle]
        translated = translate(process_lines)
        i += len(translated)
        translated_lines += translated
    sys.stderr.write("\rfinished.                \n")

    # Output formatted
    for translation, line in translated_lines:
        sys.stdout.write("%s --> %s\n" % (line, translation))


def do_snmpwalk(hostnames):
    if opt_oids and opt_extra_oids:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    if len(hostnames) == 0:
        sys.stderr.write("Please specify host names to walk on.\n")
        return

    if not os.path.exists(cmk.paths.snmpwalks_dir):
        os.makedirs(cmk.paths.snmpwalks_dir)

    for host in hostnames:
        try:
            do_snmpwalk_on(host, cmk.paths.snmpwalks_dir + "/" + host)
        except Exception, e:
            sys.stderr.write("Error walking %s: %s\n" % (host, e))
            if cmk.debug.enabled():
                raise
        cleanup_globals()


def do_snmpwalk_on(hostname, filename):
    console.verbose("%s:\n" % hostname)
    ip = ip_lookup.lookup_ipv4_address(hostname)

    out = file(filename, "w")
    oids_to_walk = opt_oids
    if not opt_oids:
        oids_to_walk = [
            ".1.3.6.1.2.1", # SNMPv2-SMI::mib-2
            ".1.3.6.1.4.1"  # SNMPv2-SMI::enterprises
        ] + opt_extra_oids

    for oid in sorted(oids_to_walk, key = lambda x: map(int, x.strip(".").split("."))):
        try:
            console.verbose("Walk on \"%s\"..." % oid)

            rows = snmp.walk_for_export(hostname, ip, oid)
            for oid, value in rows:
                out.write("%s %s\n" % (oid, value))

            console.verbose("%d variables.\n" % len(rows))
        except:
            if cmk.debug.enabled():
                raise

    out.close()
    console.verbose("Successfully Wrote %s%s%s.\n" % (tty.bold, filename, tty.normal))


def do_snmpget(oid, hostnames):
    if len(hostnames) == 0:
        for host in config.all_active_realhosts():
            if config.is_snmp_host(host):
                hostnames.append(host)

    for host in hostnames:
        ip = ip_lookup.lookup_ipv4_address(host)
        value = snmp.get_single_oid(host, ip, oid)
        sys.stdout.write("%s (%s): %r\n" % (host, ip, value))
        cleanup_globals()



def dump_all_hosts(hostlist):
    if hostlist == []:
        hostlist = config.all_active_hosts()
    for hostname in sorted(hostlist):
        dump_host(hostname)

def ip_address_for_dump_host(hostname, family=None):
    if is_cluster(hostname):
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname, family)
        except:
            ipaddress = ""
    else:
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname, family)
        except:
            ipaddress = fallback_ip_for(hostname, family)
    return ipaddress


def dump_host(hostname):
    sys.stdout.write("\n")
    if is_cluster(hostname):
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(nodes_of(hostname))) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    sys.stdout.write("%s%s%s%-78s %s\n" %
        (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = ip_address_for_dump_host(hostname)

    addresses = ""
    if not config.is_ipv4v6_host(hostname):
        addresses = ipaddress
    else:
        ipv6_primary = config.is_ipv6_primary(hostname)
        try:
            if ipv6_primary:
                secondary = ip_address_for_dump_host(hostname, 4)
            else:
                secondary = ip_address_for_dump_host(hostname, 6)
        except:
            secondary = "X.X.X.X"

        addresses = "%s, %s" % (ipaddress, secondary)
        if ipv6_primary:
            addresses += " (Primary: IPv6)"
        else:
            addresses += " (Primary: IPv4)"

    sys.stdout.write(tty.yellow + "Addresses:              " + tty.normal + addresses + "\n")

    tags = tags_of_host(hostname)
    sys.stdout.write(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")
    if is_cluster(hostname):
        parents_list = nodes_of(hostname)
    else:
        parents_list = config.parents_of(hostname)
    if len(parents_list) > 0:
        sys.stdout.write(tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n")
    sys.stdout.write(tty.yellow + "Host groups:            " + tty.normal + make_utf8(", ".join(config.hostgroups_of(hostname))) + "\n")
    sys.stdout.write(tty.yellow + "Contact groups:         " + tty.normal + make_utf8(", ".join(config.contactgroups_of(hostname))) + "\n")

    agenttypes = []
    if config.is_tcp_host(hostname):
        dapg = get_datasource_program(hostname, ipaddress)
        if dapg:
            agenttypes.append("Datasource program: %s" % dapg)
        else:
            agenttypes.append("TCP (port: %d)" % config.agent_port_of(hostname))

    if config.is_snmp_host(hostname):
        if config.is_usewalk_host(hostname):
            agenttypes.append("SNMP (use stored walk)")
        else:
            if config.is_inline_snmp_host(hostname):
                inline = "yes"
            else:
                inline = "no"

            credentials = config.snmp_credentials_of(hostname)
            if type(credentials) in [ str, unicode ]:
                cred = "community: \'%s\'" % credentials
            else:
                cred = "credentials: '%s'" % ", ".join(credentials)

            if config.is_snmpv3_host(hostname) or config.is_bulkwalk_host(hostname):
                bulk = "yes"
            else:
                bulk = "no"

            portinfo = config.snmp_port_of(hostname)
            if portinfo == None:
                portinfo = 'default'

            agenttypes.append("SNMP (%s, bulk walk: %s, port: %s, inline: %s)" %
                (cred, bulk, portinfo, inline))

    if config.is_ping_host(hostname):
        agenttypes.append('PING only')

    sys.stdout.write(tty.yellow + "Type of agent:          " + tty.normal + '\n                        '.join(agenttypes) + "\n")

    sys.stdout.write(tty.yellow + "Services:" + tty.normal + "\n")
    check_items = get_sorted_check_table(hostname)

    headers = ["checktype", "item",    "params", "description", "groups"]
    colors =  [ tty.normal,  tty.blue, tty.normal, tty.green, tty.normal ]
    if config.service_dependencies != []:
        headers.append("depends on")
        colors.append(tty.magenta)

    tty.print_table(headers, colors, [ [
        checktype,
        make_utf8(item),
        params,
        make_utf8(description),
        make_utf8(",".join(rulesets.service_extra_conf(hostname, description, config.service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")

def usage():
    sys.stdout.write("""WAYS TO CALL:
 cmk [-n] [-v] [-p] HOST [IPADDRESS]  check all services on HOST
 cmk -I [HOST ..]                     discovery - find new services
 cmk -II ...                          renew discovery, drop old services
 cmk -N [HOSTS...]                    output Nagios configuration
 cmk -B                               create configuration for core
 cmk -C, --compile                    precompile host checks
 cmk -U, --update                     precompile + create config for core
 cmk -O, --reload                     precompile + config + core reload
 cmk -R, --restart                    precompile + config + core restart
 cmk -D, --dump [H1 H2 ..]            dump all or some hosts
 cmk -d HOSTNAME|IPADDRESS            show raw information from agent
 cmk --check-discovery HOSTNAME       check for items not yet checked
 cmk --discover-marked-hosts          run discovery for hosts known to have changed services
 cmk -M, --man [CHECKTYPE]            show manpage for check CHECKTYPE
 cmk -m, --browse-man                 open interactive manpage browser
 cmk -X, --check-config               check configuration for invalid vars
 cmk --flush [HOST1 HOST2...]         flush all data of some or all hosts
 cmk --snmpwalk HOST1 HOST2 ...       Do snmpwalk on one or more hosts
 cmk --snmptranslate HOST             Do snmptranslate on walk
 cmk --snmpget OID HOST1 HOST2 ...    Fetch single OIDs and output them
 cmk --notify                         used to send notifications from core
 cmk --create-rrd [--keepalive|SPEC]  create round robin database (only CEE)
 cmk --convert-rrds [--split] [H...]  convert exiting RRD to new format (only CEE)
 cmk --handle-alerts                  alert handling, always in keepalive mode (only CEE)
 cmk --real-time-checks               process real time check results (only CEE)
 cmk -i, --inventory [HOST1 HOST2...] Do a HW/SW-Inventory of some ar all hosts
 cmk --inventory-as-check HOST        Do HW/SW-Inventory, behave like check plugin
 cmk -A, --bake-agents [-f] [H1 H2..] Bake agents for hosts (not in all versions)
 cmk -h, --help                       print this help
%s

OPTIONS:
  -v             show what's going on
  -p             also show performance data (use with -v)
  -n             do not submit results to core, do not save counters
  -c FILE        read config file FILE instead of %s
  --cache        read info from cache file is present and fresh, use TCP
                 only, if cache file is absent or too old
  --no-cache     never use cached information
  --no-tcp       for -I: only use cache files. Skip hosts without
                 cache files.
  --fake-dns IP  fake IP addresses of all hosts to be IP. This
                 prevents DNS lookups.
  --usewalk      use snmpwalk stored with --snmpwalk
  --debug        never catch Python exceptions
  --checks A,..  restrict checks/discovery to specified checks (tcp/snmp/check type)
  --keepalive    used by Check_MK Mirco Core: run check and --notify
                 in continous mode. Read data from stdin and from cmd line.
  --cmc-file=X   relative filename for CMC config file (used by -B/-U)
  --extraoid A   Do --snmpwalk also on this OID, in addition to mib-2 and enterprises.
                 You can specify this option multiple times.
  --oid A        Do --snmpwalk on this OID instead of mib-2 and enterprises.
                 You can specify this option multiple times.
  --hw-changes=S --inventory-as-check: Use monitoring state S for HW changes
  --sw-changes=S --inventory-as-check: Use monitoring state S for SW changes
  --sw-missing=S --inventory-as-check: Use monitoring state S for missing SW packages info
  --inv-fail-status=S Use monitoring state S in case if error during inventory

NOTES:
  -I can be restricted to certain check types. Write '--checks df -I' if you
  just want to look for new filesystems. Use 'check_mk -L' for a list
  of all check types. Use 'tcp' for all TCP based checks and 'snmp' for
  all SNMP based checks.

  -II does the same as -I but deletes all existing checks of the
  specified types and hosts.

  -N outputs the Nagios configuration. You may optionally add a list
  of hosts. In that case the configuration is generated only for
  that hosts (useful for debugging).

  -U redirects both the output of -S and -H to the file
  %s
  and also calls check_mk -C.

  -D, --dump dumps out the complete configuration and information
  about one, several or all hosts. It shows all services, hostgroups,
  contacts and other information about that host.

  -d does not work on clusters (such defined in main.mk) but only on
  real hosts.

  --check-discovery make check_mk behave as monitoring plugins that
  checks if a discovery would find new or vanished services for the host.
  If configured to do so, this will queue those hosts for automatic
  discover-marked-hosts

  --discover-marked-hosts run actual service discovery on all hosts that
  are known to have new/vanished services due to an earlier run of
  check-discovery. The results of this discovery may be activated
  automatically if that was discovered.

  -M, --man shows documentation about a check type. If
  /usr/bin/less is available it is used as pager. Exit by pressing
  Q. Use -M without an argument to show a list of all manual pages.

  --flush deletes all runtime data belonging to a host. This includes
  the inventorized checks, the state of performance counters,
  cached agent output, and logfiles. Precompiled host checks
  are not deleted.

  --snmpwalk does a complete snmpwalk for the specified hosts both
  on the standard MIB and the enterprises MIB and stores the
  result in the directory %s.
  Use the option --oid one or several
  times in order to specify alternative OIDs to walk. You need to
  specify numeric OIDs. If you want to keep the two standard OIDS
  .1.3.6.1.2.1  and .1.3.6.1.4.1 then use --extraoid for just adding
  additional OIDs to walk.

  --snmptranslate does not contact the host again, but reuses the hosts
  walk from the directory %s.
  You can add further MIBs to the directory
  %s.

  -A, --bake-agents creates RPM/DEB/MSI packages with host-specific
  monitoring agents. If you add the option -f, --force then all
  agents are renewed, even if an uptodate version for a configuration
  already exists. Note: baking agents is only contained in the
  subscription version of Check_MK.

  --convert-rrds converts the internal structure of existing RRDs
  to the new structure as configured via the rulesets cmc_host_rrd_config
  and cmc_service_rrd_config. If you do not specify hosts, then all
  RRDs will be converted. Conversion just takes place if the configuration
  of the RRDs has changed. The option --split will activate conversion
  from exising RRDs in PNP storage type SINGLE to MULTIPLE.

  -i, --inventory does a HW/SW-Inventory for all, one or several
  hosts. If you add the option -f, --force then persisted sections
  will be used even if they are outdated.

%s

""" % (
    modes.short_help(),
    cmk.paths.main_config_file,
    cmk.paths.precompiled_hostchecks_dir,
    cmk.paths.snmpwalks_dir,
    cmk.paths.snmpwalks_dir,
    cmk.paths.local_mibs_dir,
    modes.long_help(),
))


def do_create_config(with_agents=True):
    sys.stdout.write("Generating configuration for core (type %s)..." %
                                                config.monitoring_core)
    sys.stdout.flush()
    create_core_config()
    sys.stdout.write(tty.ok + "\n")

    if config.bake_agents_on_restart and with_agents and 'do_bake_agents' in globals():
        sys.stdout.write("Baking agents...")
        sys.stdout.flush()
        try:
            do_bake_agents()
            sys.stdout.write(tty.ok + "\n")
        except Exception, e:
            if cmk.debug.enabled():
               raise
            sys.stdout.write("Error: %s\n" % e)


def do_precompile_hostchecks():
    sys.stdout.write("Precompiling host checks...")
    sys.stdout.flush()
    precompile_hostchecks()
    sys.stdout.write(tty.ok + "\n")


def do_pack_config():
    sys.stdout.write("Packing config...")
    sys.stdout.flush()
    pack_config()
    pack_autochecks()
    sys.stdout.write(tty.ok + "\n")


def do_update(with_precompile):
    try:
        do_create_config(with_agents=with_precompile)
        if with_precompile:
            if config.monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()

    except Exception, e:
        sys.stderr.write("Configuration Error: %s\n" % e)
        if cmk.debug.enabled():
            raise
        sys.exit(1)

def do_check_nagiosconfig():
    if config.monitoring_core == 'nagios':
        command = cmk.paths.nagios_binary + " -vp "  + cmk.paths.nagios_config_file + " 2>&1"
        console.verbose("Running '%s'\n" % command)
        console.output("Validating Nagios configuration...")

        process = os.popen(command, "r")
        output = process.read()
        exit_status = process.close()
        if not exit_status:
            console.output(tty.ok + "\n")
            return True
        else:
            console.output("ERROR:\n")
            console.output(output, stream=sys.stderr)
            return False
    else:
        return True


# Action can be restart, reload, start or stop
def do_core_action(action, quiet=False):
    if not quiet:
        sys.stdout.write("%sing monitoring core..." % action.title())
        sys.stdout.flush()
    if config.monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = cmk.paths.nagios_startscript + " %s 2>&1" % action
    else:
        command = "omd %s cmc 2>&1" % action

    process = os.popen(command, "r")
    output = process.read()
    if process.close():
        if not quiet:
            sys.stdout.write("ERROR: %s\n" % output)
        raise MKGeneralException("Cannot %s the monitoring core: %s" % (action, output))
    else:
        if not quiet:
            sys.stdout.write(tty.ok + "\n")

def core_is_running():
    if config.monitoring_core == "nagios":
        command = cmk.paths.nagios_startscript + " status >/dev/null 2>&1"
    else:
        command = "omd status cmc >/dev/null 2>&1"
    code = os.system(command)
    return not code


def do_reload():
    do_restart(True)

def do_restart(only_reload = False):
    try:
        backup_path = None

        if try_get_activation_lock():
            sys.stderr.write("Other restart currently in progress. Aborting.\n")
            sys.exit(1)

        # Save current configuration
        if os.path.exists(cmk.paths.nagios_objects_file):
            backup_path = cmk.paths.nagios_objects_file + ".save"
            console.verbose("Renaming %s to %s\n", cmk.paths.nagios_objects_file, backup_path, stream=sys.stderr)
            os.rename(cmk.paths.nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
            do_create_config(with_agents=True)
        except Exception, e:
            sys.stderr.write("Error creating configuration: %s\n" % e)
            if backup_path:
                os.rename(backup_path, cmk.paths.nagios_objects_file)
            if cmk.debug.enabled():
                raise
            sys.exit(1)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            if config.monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()
            do_core_action(only_reload and "reload" or "restart")
        else:
            sys.stderr.write("Configuration for monitoring core is invalid. Rolling back.\n")

            broken_config_path = "%s/check_mk_objects.cfg.broken" % cmk.paths.tmp_dir
            file(broken_config_path, "w").write(file(cmk.paths.nagios_objects_file).read())
            sys.stderr.write("The broken file has been copied to \"%s\" for analysis.\n" % broken_config_path)

            if backup_path:
                os.rename(backup_path, cmk.paths.nagios_objects_file)
            else:
                os.remove(cmk.paths.nagios_objects_file)
            sys.exit(1)

    except Exception, e:
        try:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
        except:
            pass
        if cmk.debug.enabled():
            raise
        sys.stderr.write("An error occurred: %s\n" % e)
        sys.exit(1)

restart_lock_fd = None
def try_get_activation_lock():
    global restart_lock_fd
    # In some bizarr cases (as cmk -RR) we need to avoid duplicate locking!
    if config.restart_locking and restart_lock_fd == None:
        lock_file = cmk.paths.default_config_dir + "/main.mk"
        import fcntl
        restart_lock_fd = os.open(lock_file, os.O_RDONLY)
        # Make sure that open file is not inherited to monitoring core!
        fcntl.fcntl(restart_lock_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        try:
            if cmk.debug.enabled():
                sys.stderr.write("Waiting for exclusive lock on %s.\n" %
                    lock_file)
            fcntl.flock(restart_lock_fd, fcntl.LOCK_EX |
                ( config.restart_locking == "abort" and fcntl.LOCK_NB or 0))
        except:
            return True
    return False


# Reset some global variable to their original value. This
# is needed in keepalive mode.
# We could in fact do some positive caching in keepalive
# mode - e.g. the counters of the hosts could be saved in memory.
def cleanup_globals():
    global g_agent_already_contacted
    g_agent_already_contacted = {}
    checks.set_hostname("unknown")
    global g_item_state
    g_item_state = {}
    global g_infocache
    g_infocache = {}
    global g_agent_cache_info
    g_agent_cache_info = {}
    global g_broken_agent_hosts
    g_broken_agent_hosts = set([])
    global g_broken_snmp_hosts
    g_broken_snmp_hosts = set([])
    global g_inactive_timerperiods
    g_inactive_timerperiods = None

    snmp.cleanup_host_caches()



# Compute parameters for a check honoring factory settings,
# default settings of user in main.mk, check_parameters[] and
# the values code in autochecks (given as parameter params)
def compute_check_parameters(host, checktype, item, params):
    if checktype not in checks.check_info: # handle vanished checktype
        return None

    # Handle dictionary based checks
    def_levels_varname = checks.check_info[checktype].get("default_levels_variable")
    # TODO: Can we skip this?
    #if def_levels_varname:
    #    vars_before_config.add(def_levels_varname)

    # Handle case where parameter is None but the type of the
    # default value is a dictionary. This is for example the
    # case if a check type has gotten parameters in a new version
    # but inventory of the old version left None as a parameter.
    # Also from now on we support that the inventory simply puts
    # None as a parameter. We convert that to an empty dictionary
    # that will be updated with the factory settings and default
    # levels, if possible.
    if params == None and def_levels_varname:
        fs = checks.factory_settings.get(def_levels_varname)
        if type(fs) == dict:
            params = {}

    # Honor factory settings for dict-type checks. Merge
    # dict type checks with multiple matching rules
    if type(params) == dict:

        # Start with factory settings
        if def_levels_varname:
            new_params = checks.factory_settings.get(def_levels_varname, {}).copy()
        else:
            new_params = {}

        # Merge user's default settings onto it
        if def_levels_varname and hasattr(config, def_levels_varname):
            def_levels = getattr(config, def_levels_varname)
            if type(def_levels) == dict:
                new_params.update(def_levels)

        # Merge params from inventory onto it
        new_params.update(params)
        params = new_params

    descr = service_description(host, checktype, item)

    # Get parameters configured via checkgroup_parameters
    entries = get_checkgroup_parameters(host, checktype, item)

    # Get parameters configured via check_parameters
    entries += rulesets.service_extra_conf(host, descr, config.check_parameters)

    if entries:
        # loop from last to first (first must have precedence)
        for entry in entries[::-1]:
            if type(params) == dict and type(entry) == dict:
                params.update(entry)
            else:
                if type(entry) == dict:
                    # The entry still has the reference from the rule..
                    # If we don't make a deepcopy the rule might be modified by
                    # a followup params.update(...)
                    import copy
                    entry = copy.deepcopy(entry)
                params = entry
    return params


def get_checkgroup_parameters(host, checktype, item):
    checkgroup = checks.check_info[checktype]["group"]
    if not checkgroup:
        return []
    rules = config.checkgroup_parameters.get(checkgroup)
    if rules == None:
        return []

    try:
        # checks without an item
        if item == None and checkgroup not in service_rule_groups:
            return rulesets.host_extra_conf(host, rules)
        else: # checks with an item need service-specific rules
            return rulesets.service_extra_conf(host, item, rules)
    except MKGeneralException, e:
        raise MKGeneralException(str(e) + " (on host %s, checktype %s)" % (host, checktype))


def output_profile():
    if g_profile:
        g_profile.dump_stats(g_profile_path)
        show_profile = os.path.join(os.path.dirname(g_profile_path), 'show_profile.py')
        file(show_profile, "w")\
            .write("#!/usr/bin/python\n"
                   "import pstats\n"
                   "stats = pstats.Stats('%s')\n"
                   "stats.sort_stats('time').print_stats()\n" % g_profile_path)
        os.chmod(show_profile, 0755)

        sys.stderr.write("Profile '%s' written. Please run %s.\n" % (g_profile_path, show_profile))


#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Main entry point and option parsing. Here is where all begins.       |
#   '----------------------------------------------------------------------'

register_sigint_handler()
# TODO: Why are we loading the checks in all modes? This is useless in some modes!
checks.load()

opt_split_rrds = False
opt_delete_rrds = False
opt_log_to_stdout = False

# Do option parsing and execute main function -
short_options = 'ACURODMmd:Ic:nhvpNBif' + modes.short_options()
long_options = [ "help", "vebose", "compile", "debug",
                 "no-tcp", "cache",
                 "flush", "snmpwalk", "oid=", "extraoid=",
                 "snmptranslate", "bake-agents", "force",
                 "usewalk", "automation=", "handle-alerts", "notify",
                 "snmpget=", "profile", "keepalive", "keepalive-fd=", "create-rrd",
                 "convert-rrds", "split-rrds", "delete-rrds",
                 "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                 "man",
                 "check-inventory=", "check-discovery=", "discover-marked-hosts",
                 "checks=", "inventory", "inventory-as-check=", "hw-changes=", "sw-changes=", "sw-missing=",
                 "inv-fail-status=", "cmc-file=", "browse-man",
                 "log-to-stdout"] + modes.long_options()

non_config_options = ['-M',
                      '--handle-alerts', '--notify', '--real-time-checks',
                      '--man', '-h', '--help', '--automation',
                      '--create-rrd', '--convert-rrds', '--keepalive',
                      ] + modes.non_config_options()

try:
    opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
except getopt.GetoptError, err:
    sys.stdout.write("%s\n" % err)
    sys.exit(1)

# Read the configuration files (main.mk, autochecks, etc.), but not for
# certain operation modes that does not need them and should not be harmed
# by a broken configuration
if len(set.intersection(set(non_config_options), [o[0] for o in opts])) == 0:
    config.load()

done = False
seen_I = 0
check_types = None
exit_status = 0
opt_inv_hw_changes = 0
opt_inv_sw_changes = 0
opt_inv_sw_missing = 0
opt_inv_fail_status = 1 # State in case of an error (default: WARN)
_verbosity = 0

# Scan modifying options first (makes use independent of option order)
for o,a in opts:
    # -v/--verbose is handled above manually. Simply ignore it here.
    if o in [ '-v', '--verbose' ]:
        _verbosity += 1
    elif o in [ '-f', '--force' ]:
        opt_force = True
    elif o == '-c':
        if cmk.paths.main_config_file != a:
            sys.stderr.write("Please use the option -c separated by the other options.\n")
            sys.exit(1)
    elif o == '--cache':
        set_use_cachefile()
        enforce_using_agent_cache()
    elif o == '--no-tcp':
        opt_no_tcp = True
    elif o == '--no-cache':
        opt_no_cache = True
    elif o == '-p':
        opt_showperfdata = True
    elif o == '-n':
        opt_dont_submit = True
        item_state.continue_on_counter_wrap()
    elif o == '--fake-dns':
        ip_lookup.enforce_fake_dns(a)
    elif o == '--keepalive':
        opt_keepalive = True
    elif o == '--keepalive-fd':
        opt_keepalive_fd = int(a)
    elif o == '--usewalk':
        snmp.enforce_use_stored_walks()
        ip_lookup.enforce_localhost()
    elif o == '--oid':
        opt_oids.append(a)
    elif o == '--extraoid':
        opt_extra_oids.append(a)
    elif o == '--debug':
        cmk.debug.enable()
    elif o == '-I':
        seen_I += 1
    elif o == "--checks":
        if a == "@all":
            check_types = check_info.keys()
        else:
            check_types = a.split(",")

    elif o == "--cmc-file":
        opt_cmc_relfilename = a
    elif o == "--split-rrds":
        opt_split_rrds = True
    elif o == "--delete-rrds":
        opt_delete_rrds = True
    elif o == "--hw-changes":
        opt_inv_hw_changes = int(a)
    elif o == "--sw-changes":
        opt_inv_sw_changes = int(a)
    elif o == "--sw-missing":
        opt_inv_sw_missing = int(a)
    elif o == "--inv-fail-status":
        opt_inv_fail_status = int(a)
    elif o == "--log-to-stdout":
        opt_log_to_stdout = True

cmk.log.set_verbosity(verbosity=_verbosity)

# Perform actions (major modes)
try:
    for o, a in opts:
        if o in [ '-h', '--help' ]:
            usage()
            done = True
        elif o == '-N':
            load_module("nagios")
            do_output_nagios_conf(args)
            done = True
        elif o == '-B':
            do_update(with_precompile=False)
            done = True
        elif o in [ '-C', '--compile' ]:
            load_module("nagios")
            precompile_hostchecks()
            done = True
        elif o in [ '-U', '--update' ] :
            do_update(with_precompile=True)
            done = True
        elif o in [ '-R', '--restart' ] :
            do_restart()
            done = True
        elif o in [ '-O', '--reload' ] :
            do_reload()
            done = True
        elif o in [ '-D', '--dump' ]:
            dump_all_hosts(args)
            done = True
        elif o == '--flush':
            do_flush(args)
            done = True
        elif o == '--snmpwalk':
            do_snmpwalk(args)
            done = True
        elif o == '--snmptranslate':
            do_snmptranslate(args)
            done = True
        elif o == '--snmpget':
            do_snmpget(a, args)
            done = True
        elif o in [ '-M', '--man' ]:
            if args:
                man_pages.print_man_page(args[0])
            else:
                man_pages.print_man_page_table()
            done = True
        elif o in [ '-m', '--browse-man' ]:
            man_pages.print_man_page_browser()
            done = True
        elif o == '-d':
            output_plain_hostinfo(a)
            done = True
        elif o in [ '--check-discovery', '--check-inventory' ]:
            check_discovery(a)
            done = True
        elif o == '--discover-marked-hosts':
            discover_marked_hosts()
            done = True
        elif o == '--automation':
            load_module("automation")
            do_automation(a, args)
            done = True
        elif o in [ '-i', '--inventory' ]:
            load_module("inventory")
            if args:
                hostnames = parse_hostname_list(args, with_clusters=True)
            else:
                hostnames = None
            do_inv(hostnames)
            done = True
        elif o == '--inventory-as-check':
            load_module("inventory")
            do_inv_check(a)
            done = True

        elif o == '--handle-alerts':
            config.load(with_conf_d=True, validate_hosts=False)
            sys.exit(do_handle_alerts(args))

        elif o == '--notify':
            config.load(with_conf_d=True, validate_hosts=False)
            sys.exit(do_notify(args))

        elif o == '--real-time-checks':
            config.load(with_conf_d=True, validate_hosts=False)
            load_module("keepalive")
            load_module("real_time_checks")
            do_real_time_checks(args)
            sys.exit(0)

        elif o == '--create-rrd':
            config.load(with_conf_d=True, validate_hosts=False)
            load_module("rrd")
            do_create_rrd(args)
            done = True

        elif o == '--convert-rrds':
            config.load(with_conf_d=True)
            load_module("rrd")
            do_convert_rrds(args)
            done = True

        elif o in [ '-A', '--bake-agents' ]:
            if 'do_bake_agents' not in globals():
                raise MKBailOut("Agent baking is not implemented in your version of Check_MK. Sorry.")

            if args:
                hostnames = parse_hostname_list(args, with_clusters = False, with_foreign_hosts = True)
            else:
                hostnames = None
            do_bake_agents(hostnames)
            done = True

        elif modes.exists(o):
            modes.call(o, a, opts, args)
            done = True

    # handle -I / -II
    if not done and seen_I > 0:
        hostnames = parse_hostname_list(args)
        if not hostnames:
            opt_use_cachefile = not opt_no_cache
        do_discovery(hostnames, check_types, seen_I == 1)
        done = True

    if not done:
        if (len(args) == 0 and not opt_keepalive) or len(args) > 2:
            usage()
            sys.exit(1)

        # handle --keepalive
        elif opt_keepalive:
            load_module("keepalive")
            do_check_keepalive()

        # handle adhoc-check
        else:
            hostname = args[0]
            if len(args) == 2:
                ipaddress = args[1]
            else:
                if is_cluster(hostname):
                    ipaddress = None
                else:
                    try:
                        ipaddress = ip_lookup.lookup_ip_address(hostname)
                    except:
                        sys.stdout.write("Cannot resolve hostname '%s'.\n" % hostname)
                        sys.exit(2)

            exit_status = do_check(hostname, ipaddress, check_types)

    output_profile()
    sys.exit(exit_status)

except MKTerminate, e:
    # At top level this exception means the process has been terminated without issues.
    sys.exit(0)

except (MKGeneralException, MKBailOut), e:
    sys.stderr.write("%s\n" % e)
    if cmk.debug.enabled():
        raise
    sys.exit(3)

