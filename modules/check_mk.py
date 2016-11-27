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

# TODO: Clean up all calls and remove these aliases
tags_of_host    = config.tags_of_host
is_cluster      = config.is_cluster
is_ipv6_primary = config.is_ipv6_primary

# This is needed to make the inv_info var which is normally registered in
# inventory.py available when the file is not loaded.
# TODO: Clean this up once
inv_info = {}

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
    modules = [ 'check_mk_base', 'discovery', 'snmp', 'notify', 'events',
                 'alert_handling', 'cmc', 'inline_snmp', 'agent_bakery', 'managed' ]
    for module in modules:
        if module_exists(module):
            load_module(module)

except Exception, e:
    if cmk.debug.enabled():
        raise
    sys.stderr.write("Cannot read module %s: %s\n" % (module, e))
    sys.exit(5)


#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def output_check_info():
    all_check_manuals = man_pages.all_man_pages()

    checks_sorted = checks.check_info.items() + \
       [ ("check_" + name, entry) for (name, entry) in checks.active_check_info.items() ]
    checks_sorted.sort()
    for check_type, check in checks_sorted:
        man_filename = all_check_manuals.get(check_type)
        try:
            if 'command_line' in check:
                what = 'active'
                ty_color = tty.blue
            elif check_uses_snmp(check_type):
                what = 'snmp'
                ty_color = tty.magenta
            else:
                what = 'tcp'
                ty_color = tty.yellow

            if man_filename:
                title = file(man_filename).readlines()[0].split(":", 1)[1].strip()
            else:
                title = "(no man page present)"

            sys.stdout.write((tty.bold + "%-44s" + tty.normal
                   + ty_color + " %-6s " + tty.normal
                   + "%s\n") % \
                  (check_type, what, title))
        except Exception, e:
            sys.stderr.write("ERROR in check_type %s: %s\n" % (check_type, e))


def active_check_service_description(act_info, params):
    return sanitize_service_description(act_info["service_description"](params).replace('$HOSTNAME$', checks.g_hostname))


def active_check_arguments(hostname, description, args):
    if type(args) in [ str, unicode ]:
        return args

    elif type(args) == list:
        passwords, formated = [], []
        for arg in args:
            arg_type = type(arg)

            if arg_type in [ int, float ]:
                formated.append("%s" % arg)

            elif arg_type in [ str, unicode ]:
                formated.append(cmk_base.utils.quote_shell_string(arg))

            elif arg_type == tuple and len(arg) == 3:
                pw_ident, preformated_arg = arg[1:]
                try:
                    password = config.stored_passwords[pw_ident]["password"]
                except KeyError:
                    configuration_warning("The stored password \"%s\" used by service \"%s\" on host "
                                          "\"%s\" does not exist (anymore)." %
                                            (pw_ident, description, hostname))
                    password = "%%%"

                pw_start_index = str(preformated_arg.index("%s"))
                formated.append(cmk_base.utils.quote_shell_string(preformated_arg % ("*" * len(password))))
                passwords.append((str(len(formated)), pw_start_index, pw_ident))

            else:
                raise MKGeneralException("Invalid argument for command line: %s" % arg)

        if passwords:
            formated = [ "--pwstore=%s" % ",".join([ "@".join(p) for p in passwords ]) ] + formated

        return " ".join(formated)

    else:
        raise MKGeneralException("The check argument function needs to return either a list of arguments or a "
                                 "string of the concatenated arguments (Host: %s, Service: %s)." % (hostname, description))


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

def is_tcp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, config.tcp_hosts)

def is_ping_host(hostname):
    return not is_snmp_host(hostname) \
       and not is_tcp_host(hostname) \
       and not has_piggyback_info(hostname) \
       and not has_management_board(hostname)

def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)

def has_management_board(hostname):
    return "management_protocol" in config.host_attributes.get(hostname, {})

def management_address(hostname):
    if 'management_address' in config.host_attributes.get(hostname, {}):
        return config.host_attributes[hostname]['management_address']
    else:
        return config.ipaddresses.get(hostname)

def management_protocol(hostname):
    return config.host_attributes[hostname]['management_protocol']


# Returns a list of all hosts which are associated with this site,
# but have been removed by the "only_hosts" rule. Normally these
# are the hosts which have the tag "offline".
#
# This is not optimized for performance, so use in specific situations.
def all_offline_hosts():
    hostlist = config.filter_active_hosts(config.all_configured_realhosts().union(config.all_configured_clusters()),
                                   keep_offline_hosts=True)

    return [ hostname for hostname in hostlist
             if not rulesets.in_binary_hostlist(hostname, config.only_hosts) ]


# TODO: duplicate_hosts() is currently broken because all_active_hosts()
# now already returns sets and reduces the duplicates. Fix this?!
def duplicate_hosts():
    # Sanity check for duplicate hostnames
    seen_hostnames = set([])
    duplicates = set([])

    for hostname in config.all_active_hosts_with_duplicates():
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)

    return sorted(list(duplicates))


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

def alias_of(hostname, fallback):
    aliases = rulesets.host_extra_conf(hostname, config.extra_host_conf.get("alias", []))
    if len(aliases) == 0:
        if fallback:
            return fallback
        else:
            return hostname
    else:
        return aliases[0]



def hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, config.host_groups)

def summary_hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, config.summary_host_groups)

def host_contactgroups_of(hostlist):
    cgrs = []
    for host in hostlist:
        # host_contactgroups may take single values as well as
        # lists as item value. Of all list entries only the first
        # one is used. The single-contact-groups entries are all
        # recognized.
        first_list = True
        for entry in rulesets.host_extra_conf(host, config.host_contactgroups):
            if type(entry) == list and first_list:
                cgrs += entry
                first_list = False
            else:
                cgrs.append(entry)
    if config.monitoring_core == "nagios" and config.enable_rulebased_notifications:
        cgrs.append("check-mk-notify")
    return list(set(cgrs))


def parents_of(hostname):
    par = rulesets.host_extra_conf(hostname, config.parents)
    # Use only those parents which are defined and active in
    # all_hosts.
    used_parents = []
    for p in par:
        ps = p.split(",")
        for pss in ps:
            if pss in config.all_active_realhosts():
                used_parents.append(pss)
    return used_parents


# TODO: Remove this when checks have been moved to cmk_base.checks
hosttags_match_taglist = rulesets.hosttags_match_taglist

def convert_boolean_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        entry, rule_options = rulesets.get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        if entry[0] == NEGATE: # this entry is logically negated
            negate = True
            entry = entry[1:]
        else:
            negate = False

        if len(entry) == 2:
            hostlist, servlist = entry
            tags = []
        elif len(entry) == 3:
            tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in configuration: "
                                     "must have 2 or 3 elements" % (entry,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = rulesets.all_matching_hosts(tags, hostlist, with_foreign_hosts)
        new_rules.append((negate, hosts, rulesets.convert_pattern_list(servlist)))

    return new_rules


# Compute outcome of a service rule set that just say yes/no
def in_boolean_serviceconf_list(hostname, service_description, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in config.all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    ruleset_cache = cmk_base.config_cache.get_dict("converted_service_rulesets")
    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = convert_boolean_service_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

    cache = cmk_base.config_cache.get_dict("extraconf_servicelist")
    for negate, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service_description
            try:
                match = cache[cache_id]
            except KeyError:
                match = rulesets.in_servicematcher_list(service_matchers, service_description)
                cache[cache_id] = match

            if match:
                return not negate
    return False # no match. Do not ignore

def extra_host_conf_of(hostname, exclude=None):
    if exclude == None:
        exclude = []
    return extra_conf_of(config.extra_host_conf, hostname, None, exclude)

def extra_summary_host_conf_of(hostname):
    return extra_conf_of(config.extra_summary_host_conf, hostname, None)

# Collect all extra configuration data for a service
def extra_service_conf_of(hostname, description):
    conf = ""

    # Contact groups
    sercgr = rulesets.service_extra_conf(hostname, description, config.service_contactgroups)
    contactgroups_to_define.update(sercgr)
    if len(sercgr) > 0:
        if config.enable_rulebased_notifications:
            sercgr.append("check-mk-notify") # not nessary if not explicit groups defined
        conf += "  contact_groups\t\t" + ",".join(sercgr) + "\n"

    sergr = rulesets.service_extra_conf(hostname, description, config.service_groups)
    if len(sergr) > 0:
        conf += "  service_groups\t\t" + ",".join(sergr) + "\n"
        if config.define_servicegroups:
            servicegroups_to_define.update(sergr)
    conf += extra_conf_of(config.extra_service_conf, hostname, description)
    return conf.encode("utf-8")

def extra_summary_service_conf_of(hostname, description):
    return extra_conf_of(config.extra_summary_service_conf, hostname, description)

def extra_conf_of(confdict, hostname, service, exclude=None):
    if exclude == None:
        exclude = []

    result = ""
    for key, conflist in confdict.items():
        if service != None:
            values = rulesets.service_extra_conf(hostname, service, conflist)
        else:
            values = rulesets.host_extra_conf(hostname, conflist)

        if exclude and key in exclude:
            continue

        if values:
            format = "  %-29s %s\n"
            result += format % (key, values[0])

    return result

def autodetect_plugin(command_line):
    plugin_name = command_line.split()[0]
    if command_line[0] not in [ '$', '/' ]:
        try:
            for dir in [ "/local", "" ]:
                path = cmk.paths.omd_root + dir + "/lib/nagios/plugins/"
                if os.path.exists(path + plugin_name):
                    command_line = path + command_line
                    break
        except:
            pass
    return command_line

def host_check_command(hostname, ip, is_clust):
    # Check dedicated host check command
    values = rulesets.host_extra_conf(hostname, config.host_check_commands)
    if values:
        value = values[0]
    elif config.monitoring_core == "cmc":
        value = "smart"
    else:
        value = "ping"

    if config.monitoring_core != "cmc" and value == "smart":
        value = "ping" # avoid problems when switching back to nagios core

    if value == "smart" and not is_clust:
        return "check-mk-host-smart"

    elif value in [ "ping", "smart" ]: # Cluster host
        ping_args = check_icmp_arguments_of(hostname)
        if is_clust and ip: # Do check cluster IP address if one is there
            return "check-mk-host-ping!%s" % ping_args
        elif ping_args and is_clust: # use check_icmp in cluster mode
            return "check-mk-host-ping-cluster!%s" % ping_args
        elif ping_args: # use special arguments
            return "check-mk-host-ping!%s" % ping_args
        else:
            return None

    elif value == "ok":
        return "check-mk-host-ok"

    elif value == "agent" or value[0] == "service":
        service = value == "agent" and "Check_MK" or value[1]
        if config.monitoring_core == "cmc":
            return "check-mk-host-service!" + service
        command = "check-mk-host-custom-%d" % (len(hostcheck_commands_to_define) + 1)
        hostcheck_commands_to_define.append((command,
           'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$' %
                (hostname, service.replace('$HOSTNAME$', hostname),
                 hostname, service.replace('$HOSTNAME$', hostname))))
        return command

    elif value[0] == "tcp":
        return "check-mk-host-tcp!" + str(value[1])

    elif value[0] == "custom":
        try:
            custom_commands_to_define.add("check-mk-custom")
        except:
            pass # not needed and not available with CMC
        return "check-mk-custom!" + autodetect_plugin(value[1])

    raise MKGeneralException("Invalid value %r for host_check_command of host %s." % (
            value, hostname))


def icons_and_actions_of(what, hostname, svcdesc = None, checkname = None, params = None):
    if what == 'host':
        return list(set(rulesets.host_extra_conf(hostname, config.host_icons_and_actions)))
    else:
        actions = set(rulesets.service_extra_conf(hostname, svcdesc, config.service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if checkname:
            checkgroup = checks.check_info[checkname]["group"]
            if checkgroup in [ 'ps', 'services' ] and type(params) == dict:
                icon = params.get('icon')
                if icon:
                    actions.add(icon)

        return list(actions)


def check_icmp_arguments_of(hostname, add_defaults=True, family=None):
    values = rulesets.host_extra_conf(hostname, config.ping_levels)
    levels = {}
    for value in values[::-1]: # make first rules have precedence
        levels.update(value)
    if not add_defaults and not levels:
        return ""

    if family == None:
        family = is_ipv6_primary(hostname) and 6 or 4

    args = []

    if family == 6:
        args.append("-6")

    rta = 200, 500
    loss = 80, 100
    for key, value in levels.items():
        if key == "timeout":
            args.append("-t %d" % value)
        elif key == "packets":
            args.append("-n %d" % value)
        elif key == "rta":
            rta = value
        elif key == "loss":
            loss = value
    args.append("-w %.2f,%.2f%%" % (rta[0], loss[0]))
    args.append("-c %.2f,%.2f%%" % (rta[1], loss[1]))
    return " ".join(args)


#.
#   .--Aggregation---------------------------------------------------------.
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   +----------------------------------------------------------------------+
#   |  Service aggregations is deprecated and has been superseeded by BI.  |
#   |  This code will dropped soon. Do not use service_aggregations any    |
#   |  more...                                                             |
#   '----------------------------------------------------------------------'

# Checks if a host has service aggregations
def host_is_aggregated(hostname):
    if not config.service_aggregations:
        return False

    # host might by explicitly configured as not aggregated
    if rulesets.in_binary_hostlist(hostname, config.non_aggregated_hosts):
        return False

    # convert into host_conf_list suitable for rulesets.host_extra_conf()
    host_conf_list = [ entry[:-1] for entry in config.service_aggregations ]
    is_aggr = len(rulesets.host_extra_conf(hostname, host_conf_list)) > 0
    return is_aggr

# Determines the aggregated service name for a given
# host and service description. Returns "" if the service
# is not aggregated
def aggregated_service_name(hostname, servicedesc):
    if not config.service_aggregations:
        return ""

    for entry in config.service_aggregations:
        if len(entry) == 3:
            aggrname, hostlist, pattern = entry
            tags = []
        elif len(entry) == 4:
            aggrname, tags, hostlist, pattern = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service_aggregations: must have 3 or 4 entries" % entry)

        if len(hostlist) == 1 and hostlist[0] == "":
            sys.stderr.write('WARNING: deprecated hostlist [ "" ] in service_aggregations. Please use all_hosts instead\n')

        if rulesets.hosttags_match_taglist(tags_of_host(hostname), tags) and \
           rulesets.in_extraconf_hostlist(hostlist, hostname):
            if type(pattern) != str:
                raise MKGeneralException("Invalid entry '%r' in service_aggregations:\n "
                                         "service specification must be a string, not %s.\n" %
                                         (entry, pattern))
            matchobject = re.search(pattern, servicedesc)
            if matchobject:
                try:
                    item = matchobject.groups()[-1]
                    return aggrname % item
                except:
                    return aggrname
    return ""

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

def omd_site():
    try:
        return os.environ["OMD_SITE"]
    except KeyError:
        raise MKGeneralException(_("OMD_SITE environment variable not set. You can "
                                   "only execute this in an OMD site."))


def check_period_of(hostname, service):
    periods = rulesets.service_extra_conf(hostname, service, config.check_periods)
    if periods:
        period = periods[0]
        if period == "24X7":
            return None
        else:
            return period
    else:
        return None

def check_interval_of(hostname, checkname):
    if not check_uses_snmp(checkname):
        return # no values at all for non snmp checks
    for match, minutes in rulesets.host_extra_conf(hostname, config.snmp_check_interval):
        if match is None or match == checkname:
            return minutes # use first match

def agent_target_version(hostname):
    agent_target_versions = rulesets.host_extra_conf(hostname, config.check_mk_agent_target_versions)
    if len(agent_target_versions) > 0:
        spec = agent_target_versions[0]
        if spec == "ignore":
            return None
        elif spec == "site":
            return cmk.__version__
        elif type(spec) == str:
            # Compatibility to old value specification format (a single version string)
            return spec
        elif spec[0] == 'specific':
            return spec[1]
        else:
            return spec # return the whole spec in case of an "at least version" config


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
#   .--SNMP----------------------------------------------------------------.
#   |                      ____  _   _ __  __ ____                         |
#   |                     / ___|| \ | |  \/  |  _ \                        |
#   |                     \___ \|  \| | |\/| | |_) |                       |
#   |                      ___) | |\  | |  | |  __/                        |
#   |                     |____/|_| \_|_|  |_|_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Some basic SNMP functions. Note: most of the SNMP related code is   |
#   |  the separate module snmp.py.                                        |
#   '----------------------------------------------------------------------'

# Determine SNMP community for a specific host.  It the host is found
# int the map snmp_communities, that community is returned. Otherwise
# the snmp_default_community is returned (wich is preset with
# "public", but can be overridden in main.mk
def snmp_credentials_of(hostname):
    # TODO: this works under the assumption that we can't have the management
    #  board and the host itself queried through snmp.
    #  The alternative is a lengthy and errorprone refactoring of the whole check-
    #  call hierarchy to get the credentials passed around.
    if has_management_board(hostname)\
            and management_protocol(hostname) == "snmp":
        return config.host_attributes.get(hostname, {}).get("management_snmp_community", "public")

    try:
        return config.explicit_snmp_communities[hostname]
    except KeyError:
        pass

    communities = rulesets.host_extra_conf(hostname, config.snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return config.snmp_default_community

def get_snmp_character_encoding(hostname):
    entries = rulesets.host_extra_conf(hostname, config.snmp_character_encodings)
    if len(entries) > 0:
        return entries[0]

def is_snmpv3_host(hostname):
    return type(snmp_credentials_of(hostname)) == tuple

def is_snmp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, config.snmp_hosts)

def is_bulkwalk_host(hostname):
    if config.bulkwalk_hosts:
        return rulesets.in_binary_hostlist(hostname, config.bulkwalk_hosts)
    else:
        return False

def is_snmpv2c_host(hostname):
    return is_bulkwalk_host(hostname) or \
        rulesets.in_binary_hostlist(hostname, config.snmpv2c_hosts)

def is_usewalk_host(hostname):
    return rulesets.in_binary_hostlist(hostname, config.usewalk_hosts)


def is_inline_snmp_host(hostname):
    return has_inline_snmp and config.use_inline_snmp \
           and not rulesets.in_binary_hostlist(hostname, config.non_inline_snmp_hosts)


def snmp_timing_of(hostname):
    timing = rulesets.host_extra_conf(hostname, config.snmp_timing)
    if len(timing) > 0:
        return timing[0]
    else:
        return {}

def snmp_port_spec(hostname):
    port = snmp_port_of(hostname)
    if port == None:
        return ""
    else:
        return ":%d" % port


def snmp_proto_spec(hostname):
    if is_ipv6_primary(hostname):
        return "udp6:"
    else:
        return ""


# Returns command lines for snmpwalk and snmpget including
# options for authentication. This handles communities and
# authentication for SNMP V3. Also bulkwalk hosts
def snmp_walk_command(hostname):
    return snmp_base_command('walk', hostname) + [ "-Cc" ]

# if the credentials are a string, we use that as community,
# if it is a four-tuple, we use it as V3 auth parameters:
# (1) security level (-l)
# (2) auth protocol (-a, e.g. 'md5')
# (3) security name (-u)
# (4) auth password (-A)
# And if it is a six-tuple, it has the following additional arguments:
# (5) privacy protocol (DES|AES) (-x)
# (6) privacy protocol pass phrase (-X)
def snmp_base_command(what, hostname):
    if what == 'get':
        command = [ 'snmpget' ]
    elif what == 'getnext':
        command = [ 'snmpgetnext', '-Cf' ]
    elif is_bulkwalk_host(hostname):
        command = [ 'snmpbulkwalk' ]
    else:
        command = [ 'snmpwalk' ]

    options = []
    credentials = snmp_credentials_of(hostname)

    if type(credentials) in [ str, unicode ]:
        # Handle V1 and V2C
        if is_bulkwalk_host(hostname):
            options.append('-v2c')
        else:
            if what == 'walk':
                command = [ 'snmpwalk' ]
            if is_snmpv2c_host(hostname):
                options.append('-v2c')
            else:
                options.append('-v1')

        options += [ "-c", credentials ]

    else:
        # Handle V3
        if len(credentials) == 6:
            options += [
                "-v3", "-l", credentials[0], "-a", credentials[1],
                "-u", credentials[2], "-A", credentials[3],
                "-x", credentials[4], "-X", credentials[5],
            ]
        elif len(credentials) == 4:
            options += [
                "-v3", "-l", credentials[0], "-a", credentials[1],
                "-u", credentials[2], "-A", credentials[3],
            ]
        elif len(credentials) == 2:
            options += [
                "-v3", "-l", credentials[0], "-u", credentials[1],
            ]
        else:
            raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be "
                                     "string, 2-tuple, 4-tuple or 6-tuple" % (credentials, hostname))

    # Do not load *any* MIB files. This save lot's of CPU.
    options += [ "-m", "", "-M", "" ]

    # Configuration of timing and retries
    settings = snmp_timing_of(hostname)
    if "timeout" in settings:
        options += [ "-t", "%0.2f" % settings["timeout"] ]
    if "retries" in settings:
        options += [ "-r", "%d" % settings["retries"] ]

    return command + options

def snmp_get_oid(hostname, ipaddress, oid):
    if oid.endswith(".*"):
        oid_prefix = oid[:-2]
        commandtype = "getnext"
    else:
        oid_prefix = oid
        commandtype = "get"

    protospec = snmp_proto_spec(hostname)
    portspec = snmp_port_spec(hostname)
    command = snmp_base_command(commandtype, hostname) + \
               [ "-On", "-OQ", "-Oe", "-Ot",
                 "%s%s%s" % (protospec, ipaddress, portspec),
                 oid_prefix ]

    debug_cmd = [ "''" if a == "" else a for a in command ]
    console.vverbose("Running '%s'\n" % " ".join(debug_cmd))

    snmp_process = subprocess.Popen(command, close_fds=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exitstatus = snmp_process.wait()
    if exitstatus:
        console.verbose(tty.red + tty.bold + "ERROR: " + tty.normal + "SNMP error\n")
        console.verbose(snmp_process.stderr.read()+"\n")
        return None

    line = snmp_process.stdout.readline().strip()
    if not line:
        if cmk.debug.enabled():
            sys.stdout.write("Error in response to snmpget.\n")
        return None

    item, value = line.split("=", 1)
    value = value.strip()
    if cmk.debug.enabled():
        sys.stdout.write("SNMP answer: ==> [%s]\n" % value)
    if value.startswith('No more variables') or value.startswith('End of MIB') \
       or value.startswith('No Such Object available') or value.startswith('No Such Instance currently exists'):
        value = None

    # In case of .*, check if prefix is the one we are looking for
    if commandtype == "getnext" and not item.startswith(oid_prefix + "."):
        value = None

    # Strip quotes
    if value and value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value


def clear_other_hosts_oid_cache(hostname):
    global g_single_oid_hostname
    if g_single_oid_hostname != hostname:
        g_single_oid_cache.clear()
        g_single_oid_hostname = hostname


def set_oid_cache(hostname, oid, value):
    clear_other_hosts_oid_cache(hostname)
    g_single_oid_cache[oid] = value


def get_single_oid(hostname, ipaddress, oid):
    # New in Check_MK 1.1.11: oid can end with ".*". In that case
    # we do a snmpgetnext and try to find an OID with the prefix
    # in question. The *cache* is working including the X, however.

    if oid[0] != '.':
        if cmk.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        else:
            oid = '.' + oid

    clear_other_hosts_oid_cache(hostname)

    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    console.vverbose("       Getting OID %s: " % oid)
    if opt_use_snmp_walk or is_usewalk_host(hostname):
        walk = get_stored_snmpwalk(hostname, oid)
        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            value = walk[0][1]
        elif oid.endswith(".*") and len(walk) > 0:
            value = walk[0][1]
        else:
            value = None

    else:
        try:
            if is_inline_snmp_host(hostname):
                value = inline_snmp_get_oid(hostname, oid, ipaddress=ipaddress)
            else:
                value = snmp_get_oid(hostname, ipaddress, oid)
        except:
            if cmk.debug.enabled():
                raise
            value = None

    if value != None:
        console.vverbose("%s%s%s%s\n" % (tty.bold, tty.green, value, tty.normal))
    else:
        console.vverbose("failed.\n")

    set_oid_cache(hostname, oid, value)
    return value

#.
#   .--Cluster-------------------------------------------------------------.
#   |                    ____ _           _                                |
#   |                   / ___| |_   _ ___| |_ ___ _ __                     |
#   |                  | |   | | | | / __| __/ _ \ '__|                    |
#   |                  | |___| | |_| \__ \ ||  __/ |                       |
#   |                   \____|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Code dealing with clusters (virtual hosts that are used to deal with |
#   | services that can move between physical nodes.                       |
#   '----------------------------------------------------------------------'


# If host is node of one or more clusters, return a list of the cluster host names.
# If not, return an empty list.
def clusters_of(hostname):
    cache = cmk_base.config_cache.get_dict("clusters_of")
    if cache.is_empty():
        for cluster, hosts in config.clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                cache.setdefault(name, []).append(clustername)

    return cache.get(hostname, [])

# Determine weather a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    the_clusters = clusters_of(hostname)
    if not the_clusters:
        return hostname

    cluster_mapping = rulesets.service_extra_conf(hostname, servicedesc, config.clustered_services_mapping)
    for cluster in cluster_mapping:
        # Check if the host is in this cluster
        if cluster in the_clusters:
            return cluster

    # 1. New style: explicitly assigned services
    for cluster, conf in config.clustered_services_of.items():
        nodes = nodes_of(cluster)
        if not nodes:
            raise MKGeneralException("Invalid entry clustered_services_of['%s']: %s is not a cluster." %
                   (cluster, cluster))
        if hostname in nodes and \
            in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if in_boolean_serviceconf_list(hostname, servicedesc, config.clustered_services):
        return the_clusters[0]

    return hostname

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

    if is_ping_host(hostname):
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
        if not is_snmp_host(hostname) and is_snmp_check(checkname) and \
           (not has_management_board(hostname) or management_protocol(hostname) != "snmp"):
                passed = False
        if not is_tcp_host(hostname) and not has_piggyback_info(hostname) \
           and is_tcp_check(checkname):
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
            if hostname != host_of_clustered_service(hostname, descr):
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
                if hostname == host_of_clustered_service(node, descr):
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

        aggr_name = aggregated_service_name(hostname, description)
        params = get_precompiled_check_parameters(hostname, item, params, check_type)
        precomp_table.append((check_type, item, params, description, aggr_name)) # deps not needed while checking
    return precomp_table


def get_precompiled_check_parameters(hostname, item, params, check_type):
    precomp_func = checks.precompile_params.get(check_type)
    if precomp_func:
        return precomp_func(hostname, item, params)
    else:
        return params


# Return a list of services this services depends upon
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
        if check_uses_snmp(checkname):
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


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(hostname, family):
    cache = cmk_base.config_cache.get_dict("cached_dns_lookup")
    cache_id = hostname, family

    # Address has already been resolved in prior call to this function?
    try:
        return cache[cache_id]
    except KeyError:
        pass

    # Prepare file based fall-back DNS cache in case resolution fails
    # TODO: Find a place where this only called once!
    ip_lookup_cache = initialize_ip_lookup_cache()

    cached_ip = ip_lookup_cache.get(cache_id)
    if cached_ip and config.use_dns_cache:
        cache[cache_id] = cached_ip
        return cached_ip

    # Now do the actual DNS lookup
    try:
        ipa = socket.getaddrinfo(hostname, None, family == 4 and socket.AF_INET or socket.AF_INET6)[0][4][0]

        # Update our cached address if that has changed or was missing
        if ipa != cached_ip:
            console.verbose("Updating IPv%d DNS cache for %s: %s\n" % (family, hostname, ipa))
            update_ip_lookup_cache(cache_id, ipa)

        cache[cache_id] = ipa # Update in-memory-cache
        return ipa

    except Exception, e:
        # DNS failed. Use cached IP address if present, even if caching
        # is disabled.
        if cached_ip:
            cache[cache_id] = cached_ip
            return cached_ip
        else:
            cache[cache_id] = None
            raise MKGeneralException(
                "Failed to lookup IPv%d address of %s via DNS: %s\n" %
                (family, hostname, e))


def lookup_ipv4_address(hostname):
    return lookup_ip_address(hostname, 4)


def lookup_ipv6_address(hostname):
    return lookup_ip_address(hostname, 6)

# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(hostname, family=None):
    if family == None: # choose primary family
        family = is_ipv6_primary(hostname) and 6 or 4

    # Quick hack, where all IP addresses are faked (--fake-dns)
    if fake_dns:
        return fake_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    elif config.simulation_mode or opt_use_snmp_walk or \
         (is_usewalk_host(hostname) and is_snmp_host(hostname)):
        if family == 4:
            return "127.0.0.1"
        else:
            return "::1"

    # Now check, if IP address is hard coded by the user
    if family == 4:
        ipa = config.ipaddresses.get(hostname)
    else:
        ipa = config.ipv6addresses.get(hostname)

    if ipa:
        return ipa

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if rulesets.in_binary_hostlist(hostname, config.dyndns_hosts):
        return hostname

    return cached_dns_lookup(hostname, family)


def initialize_ip_lookup_cache():
    # Already created and initialized. Simply return it!
    if cmk_base.config_cache.exists("ip_lookup"):
        return cmk_base.config_cache.get_dict("ip_lookup")

    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")

    try:
        data_from_file = cmk.store.load_data_from_file(cmk.paths.var_dir + '/ipaddresses.cache', {})
        ip_lookup_cache.update(data_from_file)

        # be compatible to old caches which were created by Check_MK without IPv6 support
        convert_legacy_ip_lookup_cache(ip_lookup_cache)
    except:
        # TODO: Would be better to log it somewhere to make the failure transparent
        pass

    return ip_lookup_cache


def convert_legacy_ip_lookup_cache(ip_lookup_cache):
    if not ip_lookup_cache:
        return

    # New version has (hostname, ip family) as key
    if type(ip_lookup_cache.keys()[0]) == tuple:
        return

    new_cache = {}
    for key, val in ip_lookup_cache.items():
        new_cache[(key, 4)] = val
    ip_lookup_cache.clear()
    ip_lookup_cache.update(new_cache)


def update_ip_lookup_cache(cache_id, ipa):
    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")

    # Read already known data
    cache_path = cmk.paths.var_dir + '/ipaddresses.cache'
    data_from_file = cmk.store.load_data_from_file(cache_path,
                                                   default={},
                                                   lock=True)

    convert_legacy_ip_lookup_cache(data_from_file)
    ip_lookup_cache.update(data_from_file)
    ip_lookup_cache[cache_id] = ipa

    # (I don't like this)
    # TODO: this file always grows... there should be a cleanup mechanism
    #       maybe on "cmk --update-dns-cache"
    # The cache_path is already locked from a previous function call..
    cmk.store.save_data_to_file(cache_path, ip_lookup_cache)


def do_update_dns_cache():
    # Temporarily disable *use* of cache, we want to force an update
    # TODO: Cleanup this hacky config override! Better add some global flag
    # that is exactly meant for this situation.
    config.use_dns_cache = False
    updated = 0
    failed = []

    console.verbose("Updating DNS cache...\n")
    for hostname in config.all_active_hosts():
        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        for family in [ 4, 6]:
            if (family == 4 and config.is_ipv4_host(hostname)) \
               or (family == 6 and config.is_ipv6_host(hostname)):
                console.verbose("%s (IPv%d)..." % (hostname, family))
                try:
                    if family == 4:
                        ip = lookup_ipv4_address(hostname)
                    else:
                        ip = lookup_ipv6_address(hostname)

                    console.verbose("%s\n" % ip)
                    updated += 1
                except Exception, e:
                    failed.append(hostname)
                    console.verbose("lookup failed: %s\n" % e)
                    if cmk.debug.enabled():
                        raise
                    continue

    return updated, failed


def agent_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, config.agent_ports)
    if len(ports) == 0:
        return config.agent_port
    else:
        return ports[0]

def agent_encryption_settings(hostname):
    settings = rulesets.host_extra_conf(hostname, config.agent_encryption)
    if settings:
        return settings[0]
    else:
        return {'use_regular': 'disabled',
                'use_realtime': 'enforce'}

def snmp_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, config.snmp_ports)
    if len(ports) == 0:
        return None # do not specify a port, use default
    else:
        return ports[0]

def exit_code_spec(hostname):
    spec = {}
    specs = rulesets.host_extra_conf(hostname, config.check_mk_exit_status)
    for entry in specs[::-1]:
        spec.update(entry)
    return spec


# Remove illegal characters from a service description
def sanitize_service_description(descr):
    cache = cmk_base.config_cache.get_dict("sanitize_service_description")

    try:
        return cache[descr]
    except KeyError:
        new_descr = "".join([ c for c in descr if c not in config.nagios_illegal_chars ]).rstrip("\\")
        cache[descr] = new_descr
        return new_descr


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
            item_safe = sanitize_service_description(item)
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


# Get a dict that specifies the actions to be done during the hostname translation
def get_piggyback_translation(hostname):
    rules = rulesets.host_extra_conf(hostname, config.piggyback_translation)
    translations = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


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


#.
#   .--Backup & Restore----------------------------------------------------.
#   |  ____             _                   ___     ____           _       |
#   | | __ )  __ _  ___| | ___   _ _ __    ( _ )   |  _ \ ___  ___| |_     |
#   | |  _ \ / _` |/ __| |/ / | | | '_ \   / _ \/\ | |_) / _ \/ __| __|    |
#   | | |_) | (_| | (__|   <| |_| | |_) | | (_>  < |  _ <  __/\__ \ |_ _   |
#   | |____/ \__,_|\___|_|\_\\__,_| .__/   \___/\/ |_| \_\___||___/\__(_)  |
#   |                             |_|                                      |
#   +----------------------------------------------------------------------+
#   | Check_MK comes with a simple backup and restore of the current con-  |
#   | figuration and cache files (cmk --backup and cmk --restore). This is |
#   | implemented here.                                                    |
#   '----------------------------------------------------------------------'


def backup_paths():
    return [
        # tarname               path                 canonical name   description                is_dir owned_by_nagios www_group
        ('check_mk_configfile', cmk.paths.main_config_file,    "main.mk",       "Main configuration file",           False, False, False ),
        ('final_mk',            cmk.paths.final_config_file,   "final.mk",      "Final configuration file final.mk", False, False, False ),
        ('check_mk_configdir',  cmk.paths.check_mk_config_dir, "",              "Configuration sub files",           True,  False, False ),
        ('autochecksdir',       cmk.paths.autochecks_dir,      "",              "Automatically inventorized checks", True,  False, False ),
        ('counters_directory',  cmk.paths.counters_dir,        "",              "Performance counters",              True,  True,  False ),
        ('tcp_cache_dir',       cmk.paths.tcp_cache_dir,       "",              "Agent cache",                       True,  True,  False ),
        ('logwatch_dir',        cmk.paths.logwatch_dir,        "",              "Logwatch",                          True,  True,  True  ),
    ]


def do_backup(tarname):
    import tarfile
    console.verbose("Creating backup file '%s'...\n", tarname)
    tar = tarfile.open(tarname, "w:gz")

    for name, path, canonical_name, descr, is_dir, \
        _unused_owned_by_nagios, _unused_group_www in backup_paths():

        absdir = os.path.abspath(path)
        if os.path.exists(path):
            if is_dir:
                basedir = absdir
                filename = "."
                subtarname = name + ".tar"
                subdata = os.popen("tar cf - --dereference --force-local -C '%s' '%s'" % \
                                   (basedir, filename)).read()
            else:
                basedir = os.path.dirname(absdir)
                filename = os.path.basename(absdir)
                subtarname = canonical_name
                subdata = file(absdir).read()

            info = tarfile.TarInfo(subtarname)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = len(subdata)
            info.mode = 0644
            info.type = tarfile.REGTYPE
            info.name = subtarname
            console.verbose("  Added %s (%s) with a size of %s\n", descr, absdir, render.bytes(info.size))
            tar.addfile(info, StringIO(subdata))

    tar.close()
    console.verbose("Successfully created backup.\n")


def do_restore(tarname):
    import shutil

    console.verbose("Restoring from '%s'...\n", tarname)

    if not os.path.exists(tarname):
        raise MKGeneralException("Unable to restore: File does not exist")

    # TODO: Cleanup owned_by_nagios and group_www handling - not needed in pure OMD env anymore
    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths():
        absdir = os.path.abspath(path)
        if is_dir:
            basedir = absdir
            filename = "."
            if os.path.exists(absdir):
                console.verbose("  Deleting old contents of '%s'\n", absdir)
                # The path might point to a symbalic link. So it is no option
                # to call shutil.rmtree(). We must delete just the contents
                for f in os.listdir(absdir):
                    if f not in [ '.', '..' ]:
                        try:
                            p = absdir + "/" + f
                            if os.path.isdir(p):
                                shutil.rmtree(p)
                            else:
                                os.remove(p)
                        except Exception, e:
                            console.warning("  Cannot delete %s: %s", p, e)
        else:
            basedir = os.path.dirname(absdir)
            filename = os.path.basename(absdir)
            canonical_path = basedir + "/" + canonical_name
            if os.path.exists(canonical_path):
                console.verbose("  Deleting old version of '%s'\n", canonical_path)
                os.remove(canonical_path)

        if not os.path.exists(basedir):
            console.verbose("  Creating directory %s\n", basedir)
            os.makedirs(basedir)

        console.verbose("  Extracting %s (%s)\n", descr, absdir)
        if is_dir:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null "
                      "| tar xf - -C '%s' '%s' 2>/dev/null" % \
                      (tarname, name + ".tar", basedir, filename))
        else:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null > '%s' 2>/dev/null" %
                      (tarname, filename, canonical_path))

        if i_am_root():
            if owned_by_nagios:
                to_user = omd_site()
            else:
                to_user = "root"

            if group_www:
                to_group = ":%s" % omd_site()

                console.verbose("  Adding group write permissions\n")
                os.system("chmod -R g+w '%s'" % absdir)
            else:
                to_group = ":root"

            console.verbose("  Changing ownership to %s%s\n", to_user, to_group)
            os.system("chown -R '%s%s' '%s' 2>/dev/null" % (to_user, to_group, absdir))

    console.verbose("Successfully restored backup.\n")


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
        d = remove_piggyback_info_from(host)
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

g_configuration_warnings = []

def configuration_warning(text):
    g_configuration_warnings.append(text)
    sys.stdout.write("\n%sWARNING:%s %s\n" % (tty.bold + tty.yellow, tty.normal, text))


def create_core_config():
    global g_configuration_warnings
    g_configuration_warnings = []

    verify_non_duplicate_hosts()
    verify_non_deprecated_checkgroups()

    if config.monitoring_core == "cmc":
        do_create_cmc_config(opt_cmc_relfilename)
    else:
        load_module("nagios")
        out = file(cmk.paths.nagios_objects_file, "w")
        create_nagios_config(out)

    cmk.password_store.save(stored_passwords)

    num_warnings = len(g_configuration_warnings)
    if num_warnings > 10:
        g_configuration_warnings = g_configuration_warnings[:10] + \
                                  [ "%d further warnings have been omitted" % (num_warnings - 10) ]

    return g_configuration_warnings


# Verify that the user has no deprecated check groups configured.
def verify_non_deprecated_checkgroups():
    groups = checks.checks_by_checkgroup()

    for checkgroup in config.checkgroup_parameters.keys():
        if checkgroup not in groups:
            configuration_warning(
                "Found configured rules of deprecated check group \"%s\". These rules are not used "
                "by any check. Maybe this check group has been renamed during an update, "
                "in this case you will have to migrate your configuration to the new ruleset manually. "
                "Please check out the release notes of the involved versions. "
                "You may use the page \"Deprecated rules\" in WATO to view your rules and move them to "
                "the new rulesets." % checkgroup)


def verify_non_duplicate_hosts():
    duplicates = duplicate_hosts()
    if duplicates:
        configuration_warning(
              "The following host names have duplicates: %s. "
              "This might lead to invalid/incomplete monitoring for these hosts." % ", ".join(duplicates))


def verify_cluster_address_family(hostname):
    cluster_host_family = is_ipv6_primary(hostname) and "IPv6" or "IPv4"

    address_families = [
        "%s: %s" % (hostname, cluster_host_family),
    ]

    address_family = cluster_host_family
    mixed = False
    for nodename in nodes_of(hostname):
        family = is_ipv6_primary(nodename) and "IPv6" or "IPv4"
        address_families.append("%s: %s" % (nodename, family))
        if address_family == None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        configuration_warning("Cluster '%s' has different primary address families: %s" %
                                                         (hostname, ", ".join(address_families)))


def get_cluster_nodes_for_config(hostname):
    verify_cluster_address_family(hostname)

    nodes = nodes_of(hostname)[:]
    for node in nodes:
        if node not in config.all_active_realhosts():
            configuration_warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
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
        attrs["alias"] = alias_of(hostname, hostname)

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

    ipv6_primary = is_ipv6_primary(hostname)
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
    actions = icons_and_actions_of("host", hostname)
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

    if is_ipv6_primary(hostname):
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
        return lookup_ip_address(hostname, family)
    except Exception, e:
        if is_cluster(hostname):
            return ""
        else:
            g_failed_ip_lookups.append(hostname)
            if not ignore_ip_lookup_failures:
                configuration_warning("Cannot lookup IP address of '%s' (%s). "
                                      "The host will not be monitored correctly." % (hostname, e))
            return fallback_ip_for(hostname, family)


def fallback_ip_for(hostname, family=None):
    if family == None:
        family = is_ipv6_primary(hostname) and 6 or 4

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

# Create a list of all hosts of a certain hostgroup. Needed only for
# option --list-hosts
def list_all_hosts(hostgroups):
    hostlist = []
    for hn in config.all_active_hosts():
        if len(hostgroups) == 0:
            hostlist.append(hn)
        else:
            for hg in hostgroups_of(hn):
                if hg in hostgroups:
                    hostlist.append(hn)
                    break
    hostlist.sort()
    return hostlist

# Same for host tags, needed for --list-tag
def list_all_hosts_with_tags(tags):
    hosts = []

    if "offline" in tags:
        hostlist = all_offline_hosts()
    else:
        hostlist = config.all_active_hosts()

    for h in hostlist:
        if rulesets.hosttags_match_taglist(tags_of_host(h), tags):
            hosts.append(h)
    return hosts


def get_plain_hostinfo(hostname):
    info = read_cache_file(hostname, 999999999)
    if info:
        return info
    else:
        info = ""
        if is_tcp_host(hostname):
            ipaddress = lookup_ip_address(hostname)
            info += get_agent_info(hostname, ipaddress, 0)
        info += get_piggyback_info(hostname)
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
    ip = lookup_ipv4_address(hostname)

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

            if is_inline_snmp_host(hostname):
                rows = inline_snmpwalk_on_suboid(hostname, None, oid)
                rows = inline_convert_rows_for_stored_walk(rows)
            else:
                rows = snmpwalk_on_suboid(hostname, ip, oid, hex_plain = True)

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
            if is_snmp_host(host):
                hostnames.append(host)

    for host in hostnames:
        ip = lookup_ipv4_address(host)
        value = get_single_oid(host, ip, oid)
        sys.stdout.write("%s (%s): %r\n" % (host, ip, value))
        cleanup_globals()


def show_paths():
    inst = 1
    conf = 2
    data = 3
    pipe = 4
    local = 5
    dir = 1
    fil = 2

    paths = [
        ( cmk.paths.modules_dir,                 dir, inst, "Main components of check_mk"),
        ( cmk.paths.checks_dir,                  dir, inst, "Checks"),
        ( cmk.paths.notifications_dir,           dir, inst, "Notification scripts"),
        ( cmk.paths.inventory_dir,               dir, inst, "Inventory plugins"),
        ( cmk.paths.agents_dir,                  dir, inst, "Agents for operating systems"),
        ( cmk.paths.doc_dir,                     dir, inst, "Documentation files"),
        ( cmk.paths.web_dir,                     dir, inst, "Check_MK's web pages"),
        ( cmk.paths.check_manpages_dir,          dir, inst, "Check manpages (for check_mk -M)"),
        ( cmk.paths.lib_dir,                     dir, inst, "Binary plugins (architecture specific)"),
        ( cmk.paths.pnp_templates_dir,           dir, inst, "Templates for PNP4Nagios"),
    ]
    if config.monitoring_core == "nagios":
        paths += [
            ( cmk.paths.nagios_startscript,          fil, inst, "Startscript for Nagios daemon"),
            ( cmk.paths.nagios_binary,               fil, inst, "Path to Nagios executable"),
            ( cmk.paths.nagios_config_file,          fil, conf, "Main configuration file of Nagios"),
            ( cmk.paths.nagios_conf_dir,             dir, conf, "Directory where Nagios reads all *.cfg files"),
            ( cmk.paths.nagios_objects_file,         fil, data, "File into which Nagios configuration is written"),
            ( cmk.paths.nagios_status_file,          fil, data, "Path to Nagios status.dat"),
            ( cmk.paths.nagios_command_pipe_path,    fil, pipe, "Nagios' command pipe"),
            ( cmk.paths.check_result_path,           fil, pipe, "Nagios' check results directory"),
        ]

    paths += [
        ( cmk.paths.default_config_dir,          dir, conf, "Directory that contains main.mk"),
        ( cmk.paths.check_mk_config_dir,         dir, conf, "Directory containing further *.mk files"),
        ( cmk.paths.apache_config_dir,           dir, conf, "Directory where Apache reads all config files"),
        ( cmk.paths.htpasswd_file,               fil, conf, "Users/Passwords for HTTP basic authentication"),

        ( cmk.paths.var_dir,                     dir, data, "Base working directory for variable data"),
        ( cmk.paths.autochecks_dir,              dir, data, "Checks found by inventory"),
        ( cmk.paths.precompiled_hostchecks_dir,  dir, data, "Precompiled host checks"),
        ( cmk.paths.snmpwalks_dir,               dir, data, "Stored snmpwalks (output of --snmpwalk)"),
        ( cmk.paths.counters_dir,                dir, data, "Current state of performance counters"),
        ( cmk.paths.tcp_cache_dir,               dir, data, "Cached output from agents"),
        ( cmk.paths.logwatch_dir,                dir, data, "Unacknowledged logfiles of logwatch extension"),
        ( cmk.paths.livestatus_unix_socket,     fil, pipe, "Socket of Check_MK's livestatus module"),

        ( cmk.paths.local_checks_dir,           dir, local, "Locally installed checks"),
        ( cmk.paths.local_notifications_dir,    dir, local, "Locally installed notification scripts"),
        ( cmk.paths.local_inventory_dir,        dir, local, "Locally installed inventory plugins"),
        ( cmk.paths.local_check_manpages_dir,   dir, local, "Locally installed check man pages"),
        ( cmk.paths.local_agents_dir,           dir, local, "Locally installed agents and plugins"),
        ( cmk.paths.local_web_dir,              dir, local, "Locally installed Multisite addons"),
        ( cmk.paths.local_pnp_templates_dir,    dir, local, "Locally installed PNP templates"),
        ( cmk.paths.local_doc_dir,              dir, local, "Locally installed documentation"),
        ( cmk.paths.local_locale_dir,           dir, local, "Locally installed localizations"),
    ]

    def show_paths(title, t):
        if t != inst:
            sys.stdout.write("\n")
        sys.stdout.write(tty.bold + title + tty.normal + "\n")
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == dir:
                    path += "/"
                sys.stdout.write("  %-47s: %s%s%s\n" %
                    (descr, tty.bold + tty.blue, path, tty.normal))

    for title, t in [
        ( "Files copied or created during installation", inst ),
        ( "Configuration files edited by you", conf ),
        ( "Data created by Nagios/Check_MK at runtime", data ),
        ( "Sockets and pipes", pipe ),
        ( "Locally installed addons", local ),
        ]:
        show_paths(title, t)

def dump_all_hosts(hostlist):
    if hostlist == []:
        hostlist = config.all_active_hosts()
    for hostname in sorted(hostlist):
        dump_host(hostname)

def ip_address_for_dump_host(hostname, family=None):
    if is_cluster(hostname):
        try:
            ipaddress = lookup_ip_address(hostname, family)
        except:
            ipaddress = ""
    else:
        try:
            ipaddress = lookup_ip_address(hostname, family)
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
        ipv6_primary = is_ipv6_primary(hostname)
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
        parents_list = parents_of(hostname)
    if len(parents_list) > 0:
        sys.stdout.write(tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n")
    sys.stdout.write(tty.yellow + "Host groups:            " + tty.normal + make_utf8(", ".join(hostgroups_of(hostname))) + "\n")
    sys.stdout.write(tty.yellow + "Contact groups:         " + tty.normal + make_utf8(", ".join(host_contactgroups_of([hostname]))) + "\n")

    agenttypes = []
    if is_tcp_host(hostname):
        dapg = get_datasource_program(hostname, ipaddress)
        if dapg:
            agenttypes.append("Datasource program: %s" % dapg)
        else:
            agenttypes.append("TCP (port: %d)" % agent_port_of(hostname))

    if is_snmp_host(hostname):
        if is_usewalk_host(hostname):
            agenttypes.append("SNMP (use stored walk)")
        else:
            if is_inline_snmp_host(hostname):
                inline = "yes"
            else:
                inline = "no"

            credentials = snmp_credentials_of(hostname)
            if type(credentials) in [ str, unicode ]:
                cred = "community: \'%s\'" % credentials
            else:
                cred = "credentials: '%s'" % ", ".join(credentials)

            if is_snmpv3_host(hostname) or is_bulkwalk_host(hostname):
                bulk = "yes"
            else:
                bulk = "no"

            portinfo = snmp_port_of(hostname)
            if portinfo == None:
                portinfo = 'default'

            agenttypes.append("SNMP (%s, bulk walk: %s, port: %s, inline: %s)" %
                (cred, bulk, portinfo, inline))

    if is_ping_host(hostname):
        agenttypes.append('PING only')

    sys.stdout.write(tty.yellow + "Type of agent:          " + tty.normal + '\n                        '.join(agenttypes) + "\n")
    is_aggregated = host_is_aggregated(hostname)
    if is_aggregated:
        sys.stdout.write(tty.yellow + "Is aggregated:          " + tty.normal + "yes\n")
        shn = summary_hostname(hostname)
        sys.stdout.write(tty.yellow + "Summary host:           " + tty.normal + shn + "\n")
        sys.stdout.write(tty.yellow + "Summary host groups:    " + tty.normal + ", ".join(summary_hostgroups_of(hostname)) + "\n")
        sys.stdout.write(tty.yellow + "Summary contact groups: " + tty.normal + ", ".join(host_contactgroups_of([shn])) + "\n")
        notperiod = (rulesets.host_extra_conf(hostname, config.summary_host_notification_periods) + [""])[0]
        sys.stdout.write(tty.yellow + "Summary notification:   " + tty.normal + notperiod + "\n")
    else:
        sys.stdout.write(tty.yellow + "Is aggregated:          " + tty.normal + "no\n")


    sys.stdout.write(tty.yellow + "Services:" + tty.normal + "\n")
    check_items = get_sorted_check_table(hostname)

    headers = ["checktype", "item",    "params", "description", "groups", "summarized to", "groups"]
    colors =  [ tty.normal,  tty.blue, tty.normal, tty.green,     tty.normal, tty.red, tty.white ]
    if config.service_dependencies != []:
        headers.append("depends on")
        colors.append(tty.magenta)

    def if_aggr(a):
        if is_aggregated:
            return a
        else:
            return ""

    tty.print_table(headers, colors, [ [
        checktype,
        make_utf8(item),
        params,
        make_utf8(description),
        make_utf8(",".join(rulesets.service_extra_conf(hostname, description, config.service_groups))),
        if_aggr(aggregated_service_name(hostname, description)),
        if_aggr(",".join(rulesets.service_extra_conf(hostname, aggregated_service_name(hostname, description), config.summary_service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")

def print_version():
    sys.stdout.write("""This is Check_MK version %s
Copyright (C) 2009 Mathias Kettner

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; see the file COPYING.  If not, write to
    the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
    Boston, MA 02111-1307, USA.

""" % cmk.__version__)

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
 cmk --update-dns-cache               update IP address lookup cache
 cmk -l, --list-hosts [G1 G2 ...]     print list of all hosts
 cmk --list-tag TAG1 TAG2 ...         list hosts having certain tags
 cmk -L, --list-checks                list all available check types
 cmk -M, --man [CHECKTYPE]            show manpage for check CHECKTYPE
 cmk -m, --browse-man                 open interactive manpage browser
 cmk --paths                          list all pathnames and directories
 cmk -X, --check-config               check configuration for invalid vars
 cmk --backup BACKUPFILE.tar.gz       make backup of configuration and data
 cmk --restore BACKUPFILE.tar.gz      restore configuration and data
 cmk --flush [HOST1 HOST2...]         flush all data of some or all hosts
 cmk --donate                         Email data of configured hosts to MK
 cmk --snmpwalk HOST1 HOST2 ...       Do snmpwalk on one or more hosts
 cmk --snmptranslate HOST             Do snmptranslate on walk
 cmk --snmpget OID HOST1 HOST2 ...    Fetch single OIDs and output them
 cmk --scan-parents [HOST1 HOST2...]  autoscan parents, create conf.d/parents.mk
 cmk -P, --package COMMAND            do package operations
 cmk --localize COMMAND               do localization operations
 cmk --notify                         used to send notifications from core
 cmk --create-rrd [--keepalive|SPEC]  create round robin database (only CEE)
 cmk --convert-rrds [--split] [H...]  convert exiting RRD to new format (only CEE)
 cmk --compress-history FILES...      optimize monitoring history files for CMC
 cmk --handle-alerts                  alert handling, always in keepalive mode (only CEE)
 cmk --real-time-checks               process real time check results (only CEE)
 cmk -i, --inventory [HOST1 HOST2...] Do a HW/SW-Inventory of some ar all hosts
 cmk --inventory-as-check HOST        Do HW/SW-Inventory, behave like check plugin
 cmk -A, --bake-agents [-f] [H1 H2..] Bake agents for hosts (not in all versions)
 cmk --cap pack|unpack|list FILE.cap  Pack/unpack agent packages (not in all versions)
 cmk --show-snmp-stats                Analyzes recorded Inline SNMP statistics
 cmk -V, --version                    print version
 cmk -h, --help                       print this help

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
  --procs N      start up to N processes in parallel during --scan-parents
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

  --list-hosts called without argument lists all hosts. You may
  specify one or more host groups to restrict the output to hosts
  that are in at least one of those groups.

  --list-tag prints all hosts that have all of the specified tags
  at once.

  -M, --man shows documentation about a check type. If
  /usr/bin/less is available it is used as pager. Exit by pressing
  Q. Use -M without an argument to show a list of all manual pages.

  --backup saves all configuration and runtime data to a gzip
  compressed tar file. --restore *erases* the current configuration
  and data and replaces it with that from the backup file.

  --flush deletes all runtime data belonging to a host. This includes
  the inventorized checks, the state of performance counters,
  cached agent output, and logfiles. Precompiled host checks
  are not deleted.

  -P, --package brings you into packager mode. Packages are
  used to ship inofficial extensions of Check_MK. Call without
  arguments for a help on packaging.

  --localize brings you into localization mode. You can create
  and/or improve the localization of Check_MKs Multisite.  Call without
  arguments for a help on localization.

  --donate is for those who decided to help the Check_MK project
  by donating live host data. It tars the cached agent data of
  those host which are configured in main.mk:donation_hosts and sends
  them via email to donatehosts@mathias-kettner.de. The host data
  is then publicly available for others and can be used for setting
  up demo sites, implementing checks and so on.
  Do this only with test data from test hosts - not with productive
  data! By donating real-live host data you help others trying out
  Check_MK and developing checks by donating hosts. This is completely
  voluntary and turned off by default.

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

  --scan-parents uses traceroute in order to automatically detect
  hosts's parents. It creates the file conf.d/parents.mk which
  defines gateway hosts and parent declarations.

  -A, --bake-agents creates RPM/DEB/MSI packages with host-specific
  monitoring agents. If you add the option -f, --force then all
  agents are renewed, even if an uptodate version for a configuration
  already exists. Note: baking agents is only contained in the
  subscription version of Check_MK.

  --show-snmp-stats analyzes and shows a summary of the Inline SNMP
  statistics which might have been recorded on your system before.
  Note: This is only contained in the subscription version of Check_MK.

  --convert-rrds converts the internal structure of existing RRDs
  to the new structure as configured via the rulesets cmc_host_rrd_config
  and cmc_service_rrd_config. If you do not specify hosts, then all
  RRDs will be converted. Conversion just takes place if the configuration
  of the RRDs has changed. The option --split will activate conversion
  from exising RRDs in PNP storage type SINGLE to MULTIPLE.

  -i, --inventory does a HW/SW-Inventory for all, one or several
  hosts. If you add the option -f, --force then persisted sections
  will be used even if they are outdated.


""" % (cmk.paths.main_config_file,
       cmk.paths.precompiled_hostchecks_dir,
       cmk.paths.snmpwalks_dir,
       cmk.paths.snmpwalks_dir,
       cmk.paths.local_mibs_dir
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


def do_donation():
    donate = []
    cache_files = os.listdir(cmk.paths.tcp_cache_dir)
    for host in config.all_active_realhosts():
        if rulesets.in_binary_hostlist(host, config.donation_hosts):
            for f in cache_files:
                if f == host or f.startswith("%s." % host):
                    donate.append(f)
    if not donate:
        sys.stderr.write("No hosts specified. You need to set donation_hosts in main.mk.\n")
        sys.exit(1)

    console.verbose("Donating files %s\n" % " ".join(cache_files))
    import base64
    indata = base64.b64encode(os.popen("tar czf - -C %s %s" % (cmk.paths.tcp_cache_dir, " ".join(donate))).read())
    output = os.popen(config.donation_command, "w")
    output.write("\n\n@STARTDATA\n")
    while len(indata) > 0:
        line = indata[:64]
        output.write(line)
        output.write('\n')
        indata = indata[64:]


def find_bin_in_path(prog):
    for path in os.environ['PATH'].split(os.pathsep):
        f = path + '/' + prog
        if os.path.exists(f) and os.access(f, os.X_OK):
            return f

def do_scan_parents(hosts):
    if len(hosts) == 0:
        hosts = filter(lambda h: rulesets.in_binary_hostlist(h, config.scanparent_hosts), config.all_active_realhosts())

    parent_hosts = []
    parent_ips   = {}
    parent_rules = []
    gateway_hosts = set([])

    if config.max_num_processes < 1:
        config.max_num_processes = 1

    outfilename = cmk.paths.check_mk_config_dir + "/parents.mk"

    traceroute_prog = find_bin_in_path('traceroute')
    if not traceroute_prog:
        raise MKGeneralException(
           'The program "traceroute" was not found.\n'
           'The parent scan needs this program.\n'
           'Please install it and try again.')

    if os.path.exists(outfilename):
        first_line = file(outfilename, "r").readline()
        if not first_line.startswith('# Automatically created by --scan-parents at'):
            raise MKGeneralException("conf.d/parents.mk seems to be created manually.\n\n"
                                     "The --scan-parents function would overwrite this file.\n"
                                     "Please rename it to keep the configuration or delete "
                                     "the file and try again.")

    sys.stdout.write("Scanning for parents (%d processes)..." % config.max_num_processes)
    sys.stdout.flush()
    while len(hosts) > 0:
        chunk = []
        while len(chunk) < config.max_num_processes and len(hosts) > 0:
            host = hosts[0]
            del hosts[0]
            # skip hosts that already have a parent
            if len(parents_of(host)) > 0:
                console.verbose("(manual parent) ")
                continue
            chunk.append(host)

        gws = scan_parents_of(chunk)

        for host, (gw, _unused_state, _unused_ping_fails, _unused_message) in zip(chunk, gws):
            if gw:
                gateway, gateway_ip, dns_name = gw
                if not gateway: # create artificial host
                    if dns_name:
                        gateway = dns_name
                    else:
                        gateway = "gw-%s" % (gateway_ip.replace(".", "-"))
                    if gateway not in gateway_hosts:
                        gateway_hosts.add(gateway)
                        parent_hosts.append("%s|parent|ping" % gateway)
                        parent_ips[gateway] = gateway_ip
                        if config.monitoring_host:
                            parent_rules.append( (config.monitoring_host, [gateway]) ) # make Nagios a parent of gw
                parent_rules.append( (gateway, [host]) )
            elif host != config.monitoring_host and config.monitoring_host:
                # make monitoring host the parent of all hosts without real parent
                parent_rules.append( (config.monitoring_host, [host]) )

    out = file(outfilename, "w")
    out.write("# Automatically created by --scan-parents at %s\n\n" % time.asctime())
    out.write("# Do not edit this file. If you want to convert an\n")
    out.write("# artificial gateway host into a permanent one, then\n")
    out.write("# move its definition into another *.mk file\n")

    out.write("# Parents which are not listed in your all_hosts:\n")
    out.write("all_hosts += %s\n\n" % pprint.pformat(parent_hosts))

    out.write("# IP addresses of parents not listed in all_hosts:\n")
    out.write("ipaddresses.update(%s)\n\n" % pprint.pformat(parent_ips))

    out.write("# Parent definitions\n")
    out.write("parents += %s\n\n" % pprint.pformat(parent_rules))
    sys.stdout.write("\nWrote %s\n" % outfilename)

def gateway_reachable_via_ping(ip, probes):
    return 0 == os.system("ping -q -i 0.2 -l 3 -c %d -W 5 %s >/dev/null 2>&1" %
      (probes, cmk_base.utils.quote_shell_string(ip))) >> 8

def scan_parents_of(hosts, silent=False, settings=None):
    if settings is None:
        settings = {}

    if config.monitoring_host:
        nagios_ip = lookup_ipv4_address(config.monitoring_host)
    else:
        nagios_ip = None

    os.putenv("LANG", "")
    os.putenv("LC_ALL", "")

    # Start processes in parallel
    procs = []
    for host in hosts:
        console.verbose("%s " % host)
        try:
            ip = lookup_ipv4_address(host)
            command = "traceroute -w %d -q %d -m %d -n %s 2>&1" % (
                settings.get("timeout", 8),
                settings.get("probes", 2),
                settings.get("max_ttl", 10),
                cmk_base.utils.quote_shell_string(ip))
            if cmk.debug.enabled():
                sys.stderr.write("Running '%s'\n" % command)
            procs.append( (host, ip, os.popen(command) ) )
        except:
            procs.append( (host, None, os.popen(
                "echo 'ERROR: cannot resolve host name'")))

    # Output marks with status of each single scan
    def dot(color, dot='o'):
        if not silent:
            sys.stdout.write(tty.bold + color + dot + tty.normal)
            sys.stdout.flush()

    # Now all run and we begin to read the answers. For each host
    # we add a triple to gateways: the gateway, a scan state  and a diagnostic output
    gateways = []
    for host, ip, proc in procs:
        lines = [l.strip() for l in proc.readlines()]
        exitstatus = proc.close()
        if exitstatus:
            dot(tty.red, '*')
            gateways.append((None, "failed", 0, "Traceroute failed with exit code %d" % (exitstatus & 255)))
            continue

        if len(lines) == 1 and lines[0].startswith("ERROR:"):
            message = lines[0][6:].strip()
            console.verbose("%s: %s\n", host, message, stream=sys.stderr)
            dot(tty.red, "D")
            gateways.append((None, "dnserror", 0, message))
            continue

        elif len(lines) == 0:
            if cmk.debug.enabled():
                raise MKGeneralException("Cannot execute %s. Is traceroute installed? Are you root?" % command)
            else:
                dot(tty.red, '!')
            continue

        elif len(lines) < 2:
            if not silent:
                sys.stderr.write("%s: %s\n" % (host, ' '.join(lines)))
            gateways.append((None, "garbled", 0, "The output of traceroute seem truncated:\n%s" %
                    ("".join(lines))))
            dot(tty.blue)
            continue

        # Parse output of traceroute:
        # traceroute to 8.8.8.8 (8.8.8.8), 30 hops max, 40 byte packets
        #  1  * * *
        #  2  10.0.0.254  0.417 ms  0.459 ms  0.670 ms
        #  3  172.16.0.254  0.967 ms  1.031 ms  1.544 ms
        #  4  217.0.116.201  23.118 ms  25.153 ms  26.959 ms
        #  5  217.0.76.134  32.103 ms  32.491 ms  32.337 ms
        #  6  217.239.41.106  32.856 ms  35.279 ms  36.170 ms
        #  7  74.125.50.149  45.068 ms  44.991 ms *
        #  8  * 66.249.94.86  41.052 ms 66.249.94.88  40.795 ms
        #  9  209.85.248.59  43.739 ms  41.106 ms 216.239.46.240  43.208 ms
        # 10  216.239.48.53  45.608 ms  47.121 ms 64.233.174.29  43.126 ms
        # 11  209.85.255.245  49.265 ms  40.470 ms  39.870 ms
        # 12  8.8.8.8  28.339 ms  28.566 ms  28.791 ms
        routes = []
        for line in lines[1:]:
            parts = line.split()
            route = parts[1]
            if route.count('.') == 3:
                routes.append(route)
            elif route == '*':
                routes.append(None) # No answer from this router
            else:
                if not silent:
                    sys.stderr.write("%s: invalid output line from traceroute: '%s'\n" % (host, line))

        if len(routes) == 0:
            error = "incomplete output from traceroute. No routes found."
            sys.stderr.write("%s: %s\n" % (host, error))
            gateways.append((None, "garbled", 0, error))
            dot(tty.red)
            continue

        # Only one entry -> host is directly reachable and gets nagios as parent -
        # if nagios is not the parent itself. Problem here: How can we determine
        # if the host in question is the monitoring host? The user must configure
        # this in monitoring_host.
        elif len(routes) == 1:
            if ip == nagios_ip:
                gateways.append( (None, "root", 0, "") ) # We are the root-monitoring host
                dot(tty.white, 'N')
            elif config.monitoring_host:
                gateways.append( ((config.monitoring_host, nagios_ip, None), "direct", 0, "") )
                dot(tty.cyan, 'L')
            else:
                gateways.append( (None, "direct", 0, "") )
            continue

        # Try far most route which is not identical with host itself
        ping_probes = settings.get("ping_probes", 5)
        skipped_gateways = 0
        route = None
        for r in routes[::-1]:
            if not r or (r == ip):
                continue
            # Do (optional) PING check in order to determine if that
            # gateway can be monitored via the standard host check
            if ping_probes:
                if not gateway_reachable_via_ping(r, ping_probes):
                    console.verbose("(not using %s, not reachable)\n", r, stream=sys.stderr)
                    skipped_gateways += 1
                    continue
            route = r
            break
        if not route:
            error = "No usable routing information"
            if not silent:
                sys.stderr.write("%s: %s\n" % (host, error))
            gateways.append((None, "notfound", 0, error))
            dot(tty.blue)
            continue

        # TTLs already have been filtered out)
        gateway_ip = route
        gateway = ip_to_hostname(route)
        if gateway:
            console.verbose("%s(%s) ", gateway, gateway_ip)
        else:
            console.verbose("%s ", gateway_ip)

        # Try to find DNS name of host via reverse DNS lookup
        dns_name = ip_to_dnsname(gateway_ip)
        gateways.append( ((gateway, gateway_ip, dns_name), "gateway", skipped_gateways, "") )
        dot(tty.green, 'G')
    return gateways

# find hostname belonging to an ip address. We must not use
# reverse DNS but the Check_MK mechanisms, since we do not
# want to find the DNS name but the name of a matching host
# from all_hosts

ip_to_hostname_cache = None
def ip_to_hostname(ip):
    global ip_to_hostname_cache
    if ip_to_hostname_cache == None:
        ip_to_hostname_cache = {}
        for host in config.all_active_realhosts():
            try:
                ip_to_hostname_cache[lookup_ipv4_address(host)] = host
            except:
                pass
    return ip_to_hostname_cache.get(ip)

def ip_to_dnsname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return None

def config_timestamp():
    mtime = 0
    for dirpath, _unused_dirnames, filenames in os.walk(cmk.paths.check_mk_config_dir):
        for f in filenames:
            mtime = max(mtime, os.stat(dirpath + "/" + f).st_mtime)

    for path in [ cmk.paths.main_config_file, cmk.paths.final_config_file, cmk.paths.local_config_file ]:
        try:
            mtime = max(mtime, os.stat(path).st_mtime)
        except:
            pass
    return mtime



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
    global g_walk_cache
    g_walk_cache = {}
    global g_timeout
    g_timeout = None
    clear_other_hosts_oid_cache(None)

    if has_inline_snmp:
        cleanup_inline_snmp_globals()



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
        if def_levels_varname and (def_levels_varname in globals()):
            def_levels = eval(def_levels_varname)
            if type(def_levels) == dict:
                new_params.update(eval(def_levels_varname))

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
checks.load()

opt_split_rrds = False
opt_delete_rrds = False
opt_log_to_stdout = False

# Do option parsing and execute main function -
short_options = 'ASHVLCURODMmd:Ic:nhvpXPNBilf'
long_options = [ "help", "version", "verbose", "compile", "debug",
                 "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
                 "flush", "package", "localize", "donate", "snmpwalk", "oid=", "extraoid=",
                 "snmptranslate", "bake-agents", "force", "show-snmp-stats",
                 "usewalk", "scan-parents", "procs=", "automation=", "handle-alerts", "notify",
                 "snmpget=", "profile", "keepalive", "keepalive-fd=", "create-rrd",
                 "convert-rrds", "compress-history", "split-rrds", "delete-rrds",
                 "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                 "man", "config-check", "backup=", "restore=",
                 "check-inventory=", "check-discovery=", "discover-marked-hosts", "paths",
                 "checks=", "inventory", "inventory-as-check=", "hw-changes=", "sw-changes=", "sw-missing=",
                 "inv-fail-status=", "cmc-file=", "browse-man", "update-dns-cache", "cap", "real-time-checks",
                 "log-to-stdout"]

non_config_options = ['-L', '--list-checks', '-P', '--package', '-M',
                      '--handle-alerts', '--notify', '--real-time-checks',
                      '--man', '-V', '--version' ,'-h', '--help', '--automation',
                      '--create-rrd', '--convert-rrds', '--compress-history', '--keepalive', '--cap' ]

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
        fake_dns = a
    elif o == '--keepalive':
        opt_keepalive = True
    elif o == '--keepalive-fd':
        opt_keepalive_fd = int(a)
    elif o == '--usewalk':
        opt_use_snmp_walk = True
    elif o == '--oid':
        opt_oids.append(a)
    elif o == '--extraoid':
        opt_extra_oids.append(a)
    elif o == '--procs':
        config.max_num_processes = int(a)
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
        elif o in [ '-V', '--version' ]:
            print_version()
            done = True
        elif o in [ '-X', '--config-check' ]:
            done = True
        elif o in [ '-S', '-H' ]:
            sys.stderr.write(tty.bold + tty.red + "ERROR" + tty.normal + "\n")
            sys.stderr.write("The options -S and -H have been replaced with the option -N. If you \n")
            sys.stderr.write("want to generate only the service definitions, please set \n")
            sys.stderr.write("'generate_hostconf = False' in main.mk.\n")
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
        elif o == '--backup':
            do_backup(a)
            done = True
        elif o ==  '--restore':
            do_restore(a)
            done = True
        elif o == '--flush':
            do_flush(args)
            done = True
        elif o == '--paths':
            show_paths()
            done = True
        elif o in ['-P', '--package']:
            import cmk_base.packaging
            cmk_base.packaging.do_packaging(args)
            done = True
        elif o in ['--localize']:
            import cmk_base.localize
            cmk_base.localize.do_localize(args)
            done = True
        elif o == '--donate':
            do_donation()
            done = True
        elif o == '--update-dns-cache':
            do_update_dns_cache()
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
        elif o in [ '-l', '--list-hosts' ]:
            l = list_all_hosts(args)
            sys.stdout.write("\n".join(l))
            if l != []:
                sys.stdout.write("\n")
            done = True
        elif o == '--list-tag':
            l = list_all_hosts_with_tags(args)
            sys.stdout.write("\n".join(l))
            if l != []:
                sys.stdout.write("\n")
            done = True
        elif o in [ '-L', '--list-checks' ]:
            output_check_info()
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
        elif o == '--scan-parents':
            do_scan_parents(args)
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

        elif o == '--compress-history':
            import cmk_base.compress_history
            cmk_base.compress_history.do_compress_history(args)
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

        elif o == '--cap':
            try:
                import cmk_base.cee.cap
            except ImportError:
                raise MKBailOut("Agent packages are not supported by your version of Check_MK.")

            cmk_base.cee.cap.do_cap(args)
            done = True

        elif o in [ '--show-snmp-stats' ]:
            if 'do_show_snmp_stats' not in globals():
                sys.stderr.write("Handling of SNMP statistics is not implemented in your version of Check_MK. Sorry.\n")
                sys.exit(1)
            do_show_snmp_stats()
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
                        ipaddress = lookup_ip_address(hostname)
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

