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

# Future convention within all Check_MK modules for variable names:
#
# - host_name     - Monitoring name of a host (string)
# - node_name     - Name of cluster member (string)
# - cluster_name  - Name of a cluster (string)
# - realhost_name - Name of a *real* host, not a cluster (string)

import os
import sys
import time
import socket
import getopt
import re
import stat
import urllib
import subprocess
import fcntl
import py_compile
import inspect

# These variable will be substituted at 'make dist' time
check_mk_version  = '(inofficial)'

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

opt_debug        = '--debug' in sys.argv[1:]
opt_interactive  = '--interactive' in sys.argv[1:]
opt_verbose      = ('-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]) and 1 or 0

if '--profile' in sys.argv[1:]:
    import cProfile
    g_profile = cProfile.Profile()
    g_profile.enable()
    if opt_verbose:
        sys.stderr.write("Enabled profiling.\n")


#.
#   .--Pathnames-----------------------------------------------------------.
#   |        ____       _   _                                              |
#   |       |  _ \ __ _| |_| |__  _ __   __ _ _ __ ___   ___  ___          |
#   |       | |_) / _` | __| '_ \| '_ \ / _` | '_ ` _ \ / _ \/ __|         |
#   |       |  __/ (_| | |_| | | | | | | (_| | | | | | |  __/\__ \         |
#   |       |_|   \__,_|\__|_| |_|_| |_|\__,_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# are we running OMD? If yes, honor local/ hierarchy
omd_root = os.getenv("OMD_ROOT", None)
if omd_root:
    local_share              = omd_root + "/local/share/check_mk"
    local_checks_dir         = local_share + "/checks"
    local_notifications_dir  = local_share + "/notifications"
    local_inventory_dir      = local_share + "/inventory"
    local_check_manpages_dir = local_share + "/checkman"
    local_agents_dir         = local_share + "/agents"
    local_special_agents_dir = local_agents_dir + "/special"
    local_mibs_dir           = local_share + "/mibs"
    local_web_dir            = local_share + "/web"
    local_pnp_templates_dir  = local_share + "/pnp-templates"
    local_doc_dir            = omd_root + "/local/share/doc/check_mk"
    local_locale_dir         = local_share + "/locale"
    local_bin_dir            = omd_root + "/local/bin"
    local_lib_dir            = omd_root + "/local/lib"
else:
    local_checks_dir         = None
    local_notifications_dir  = None
    local_inventory_dir      = None
    local_check_manpages_dir = None
    local_agents_dir         = None
    local_special_agents_dir = None
    local_mibs_dir           = None
    local_web_dir            = None
    local_pnp_templates_dir  = None
    local_doc_dir            = None
    local_locale_dir         = None
    local_bin_dir            = None
    local_lib_dir            = None

# Pathnames, directories   and  other  settings.  All  these  settings
# should be  overriden by  /usr/share/check_mk/modules/defaults, which
# is created by setup.sh. The user might override those values again
# in main.mk

default_config_dir                 = '/etc/check_mk'
check_mk_configdir                 = default_config_dir + "/conf.d"
checks_dir                         = '/usr/share/check_mk/checks'
notifications_dir                  = '/usr/share/check_mk/notifications'
inventory_dir                      = '/usr/share/check_mk/inventory'
agents_dir                         = '/usr/share/check_mk/agents'
check_manpages_dir                 = '/usr/share/doc/check_mk/checks'
modules_dir                        = '/usr/share/check_mk/modules'
var_dir                            = '/var/lib/check_mk'
autochecksdir                      = var_dir + '/autochecks'
snmpwalks_dir                      = var_dir + '/snmpwalks'
precompiled_hostchecks_dir         = var_dir + '/precompiled'
counters_directory                 = var_dir + '/counters'
tcp_cache_dir                      = var_dir + '/cache'
logwatch_dir                       = var_dir + '/logwatch'
www_group                          = None # unset
logwatch_notes_url                 = "/nagios/logwatch.php?host=%s&file=%s"
rrdcached_socket                   = None
rrd_path                           = None

# Stuff for supporting Nagios
check_result_path                  = '/usr/local/nagios/var/spool/checkresults'
nagios_objects_file                = var_dir + '/check_mk_objects.cfg'
nagios_command_pipe_path           = '/usr/local/nagios/var/rw/nagios.cmd'
nagios_startscript                 = '/etc/init.d/nagios'
nagios_binary                      = '/usr/sbin/nagios'
nagios_config_file                 = '/etc/nagios/nagios.cfg'

# During setup a file called defaults is created in the modules
# directory.  In this file all directories are configured.  We need to
# read in this file first. It tells us where to look for our
# configuration file. In python argv[0] always contains the directory,
# even if the binary lies in the PATH and is called without
# '/'. This allows us to find our directory by taking everything up to
# the first '/'

# Allow to specify defaults file on command line (needed for OMD)
if len(sys.argv) >= 2 and sys.argv[1] == '--defaults':
    defaults_path = sys.argv[2]
    del sys.argv[1:3]
else:
    defaults_path = os.path.dirname(sys.argv[0]) + "/defaults"

try:
    execfile(defaults_path)
except Exception, e:
    sys.stderr.write(("ERROR: Cannot read installation settings of check_mk.\n%s\n\n"+
                      "During setup the file '%s'\n"+
                      "should have been created. Please make sure that that file\n"+
                      "exists, is readable and contains valid Python code.\n") %
                     (e, defaults_path))
    sys.exit(3)

# Now determine the location of the directory containing main.mk. It
# is searched for at several places:
#
# 1. if present - the option '-c' specifies the path to main.mk
# 2. in the default_config_dir (that path should be present in modules/defaults)

try:
    i = sys.argv.index('-c')
    if i > 0 and i < len(sys.argv)-1:
        check_mk_configfile = sys.argv[i+1]
        parts = check_mk_configfile.split('/')
        if len(parts) > 1:
            check_mk_basedir = check_mk_configfile.rsplit('/',1)[0]
        else:
            check_mk_basedir = "." # no / contained in filename

        if not os.path.exists(check_mk_basedir):
            sys.stderr.write("Directory %s does not exist.\n" % check_mk_basedir)
            sys.exit(1)

        if not os.path.exists(check_mk_configfile):
            sys.stderr.write("Missing configuration file %s.\n" % check_mk_configfile)
            sys.exit(1)

        # Also rewrite the location of the conf.d directory
        if os.path.exists(check_mk_basedir + "/conf.d"):
            check_mk_configdir = check_mk_basedir + "/conf.d"

    else:
        sys.stderr.write("Missing argument to option -c.\n")
        sys.exit(1)

except ValueError:
    if not os.path.exists(default_config_dir + "/main.mk"):
        sys.stderr.write("Missing main configuration file %s/main.mk\n" % default_config_dir)
        sys.exit(4)
    check_mk_basedir = default_config_dir
    check_mk_configfile = check_mk_basedir + "/main.mk"

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
PHYSICAL_HOSTS = [ '@physical' ] # all hosts but not clusters
CLUSTER_HOSTS  = [ '@cluster' ]  # all cluster hosts
ALL_HOSTS      = [ '@all' ]      # physical and cluster hosts
ALL_SERVICES   = [ "" ]          # optical replacement"
NEGATE         = '@negate'       # negation in boolean lists

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
    "hyperv_vm"                        : "hyperv_vms",
    "ibm_svc_mdiskgrp"                 : "MDiskGrp %s",
    "ibm_svc_system"                   : "IBM SVC Info",
    "ibm_svc_systemstats.diskio"       : "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats.iops"         : "IBM SVC IOPS %s Total",
    "ibm_svc_systemstats.disk_latency" : "IBM SVC Latency %s Total",
    "ibm_svc_systemstats.cache"        : "IBM SVC Cache Total",

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
    path = modules_dir + "/" + name + ".py"
    return os.path.exists(path)

def load_module(name):
    path = modules_dir + "/" + name + ".py"
    execfile(path, globals())

known_vars = set(vars().keys())
known_vars.add('known_vars')
load_module("config")
config_variable_names = set(vars().keys()).difference(known_vars)

# at check time (and many of what is also needed at administration time).
try:
    modules = [ 'check_mk_base', 'discovery', 'snmp', 'agent_simulator', 'notify', 'events',
                 'alert_handling', 'prediction', 'cmc', 'inline_snmp', 'agent_bakery', 'cap' ]
    for module in modules:
        if module_exists(module):
            load_module(module)

except Exception, e:
    sys.stderr.write("Cannot read module %s: %s\n" % (module, e))
    sys.exit(5)


#.
#   .--Check helpers ------------------------------------------------------.
#   |     ____ _               _      _          _                         |
#   |    / ___| |__   ___  ___| | __ | |__   ___| |_ __   ___ _ __ ___     |
#   |   | |   | '_ \ / _ \/ __| |/ / | '_ \ / _ \ | '_ \ / _ \ '__/ __|    |
#   |   | |___| | | |  __/ (__|   <  | | | |  __/ | |_) |  __/ |  \__ \    |
#   |    \____|_| |_|\___|\___|_|\_\ |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                                             |_|                      |
#   +----------------------------------------------------------------------+
#   | These functions are used by some checks at administration time.      |
#   +----------------------------------------------------------------------+

# The function no_discovery_possible is as stub function used for
# those checks that do not support inventory. It must be known before
# we read in all the checks
def no_discovery_possible(check_type, info):
    if opt_verbose:
        sys.stdout.write("%s does not support discovery. Skipping it.\n" % check_type)
    return []



#.
#   .--Load checks---------------------------------------------------------.
#   |       _                    _        _               _                |
#   |      | |    ___   __ _  __| |   ___| |__   ___  ___| | _____         |
#   |      | |   / _ \ / _` |/ _` |  / __| '_ \ / _ \/ __| |/ / __|        |
#   |      | |__| (_) | (_| | (_| | | (__| | | |  __/ (__|   <\__ \        |
#   |      |_____\___/ \__,_|\__,_|  \___|_| |_|\___|\___|_|\_\___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# The following data structures will be filled by the checks
check_info                         = {} # all known checks
inv_info                           = {} # inventory plugins
checkgroup_of                      = {} # groups of checks with compatible parametration
check_includes                     = {} # library files needed by checks
precompile_params                  = {} # optional functions for parameter precompilation
check_default_levels               = {} # dictionary-configured checks declare their default level variables here
factory_settings                   = {} # factory settings for dictionary-configured checks
check_config_variables             = [] # variables (names) in checks/* needed for check itself
snmp_info                          = {} # whichs OIDs to fetch for which check (for tabular information)
snmp_scan_functions                = {} # SNMP autodetection
active_check_info                  = {} # definitions of active "legacy" checks
special_agent_info                 = {}

# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values user can override those variables in his configuration.
# If a check or check.include is both found in local/ and in the
# normal structure, then only the file in local/ must be read!
def load_checks():
    filelist = plugin_pathnames_in_directory(local_checks_dir) \
             + plugin_pathnames_in_directory(checks_dir)

    # read include files always first, but still in the sorted
    # order with local ones last (possibly overriding variables)
    filelist = [ f for f in filelist if f.endswith(".include") ] + \
               [ f for f in filelist if not f.endswith(".include") ]

    varname = None
    value = None
    ignored_variable_types = [ type(lambda: None), type(os) ]

    known_vars = set(globals().keys()) # track new configuration variables

    loaded_files = set()
    for f in filelist:
        if not f.endswith("~"): # ignore emacs-like backup files
            file_name = f.rsplit("/", 1)[-1]
            if file_name not in loaded_files:
                try:
                    loaded_files.add(file_name)
                    execfile(f, globals())
                except Exception, e:
                    sys.stderr.write("Error in plugin file %s: %s\n" % (f, e))
                    if opt_debug:
                        raise
                    # If we exit here, from a check_mk helper, check_mk will just
                    # try to restart the helper. This causes a tight loop of helper
                    # crashing and helper restarting that spams the log file and
                    # causes high cpu load which is a bit pointless because an
                    # invalid plugin file isn't going to fix itself
                    #sys.exit(5)

    for varname, value in globals().iteritems():
        if varname[0] != '_' \
            and varname not in known_vars \
            and type(value) not in ignored_variable_types:
            config_variable_names.add(varname)

    # Now convert check_info to new format.
    convert_check_info()
    verify_checkgroup_members()


def checks_by_checkgroup():
    groups = {}
    for check_type, check in check_info.items():
        group_name = check["group"]
        if group_name:
            groups.setdefault(group_name, [])
            groups[group_name].append((check_type, check))
    return groups


# This function validates the checks which are members of checkgroups to have either
# all or none an item. Mixed checkgroups lead to strange exceptions when processing
# the check parameters. So it is much better to catch these errors in a central place
# with a clear error message.
def verify_checkgroup_members():
    groups = checks_by_checkgroup()

    for group_name, checks in groups.items():
        with_item, without_item = [], []
        for check_type, check in checks:
            # Trying to detect whether or not the check has an item. But this mechanism is not
            # 100% reliable since Check_MK appends an item to the service_description when "%s"
            # is not in the checks service_description template.
            # Maybe we need to define a new rule which enforces the developer to use the %s in
            # the service_description. At least for grouped checks.
            if "%s" in check["service_description"]:
                with_item.append(check_type)
            else:
                without_item.append(check_type)

        if with_item and without_item:
            raise MKGeneralException("Checkgroup %s has checks with and without item! At least one of "
                                     "the checks in this group needs to be changed (With item: %s, "
                                     "Without item: %s)" % (group_name, ", ".join(with_item), ", ".join(without_item)))


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
    all_check_manuals = all_manuals()
    read_manpage_catalog()

    checks_sorted = check_info.items() + \
       [ ("check_" + name, entry) for (name, entry) in active_check_info.items() ]
    checks_sorted.sort()
    for check_type, check in checks_sorted:
        man_filename = all_check_manuals.get(check_type)
        try:
            if 'command_line' in check:
                what = 'active'
                ty_color = tty_blue
            elif check_uses_snmp(check_type):
                what = 'snmp'
                ty_color = tty_magenta
            else:
                what = 'tcp'
                ty_color = tty_yellow

            if man_filename:
                title = file(man_filename).readlines()[0].split(":", 1)[1].strip()
            else:
                title = "(no man page present)"

            print (tty_bold + "%-44s" + tty_normal
                   + ty_color + " %-6s " + tty_normal
                   + "%s") % \
                  (check_type, what, title)
        except Exception, e:
            sys.stderr.write("ERROR in check_type %s: %s\n" % (check_type, e))


def active_check_service_description(act_info, params):
    return sanitize_service_description(act_info["service_description"](params).replace('$HOSTNAME$', g_hostname))


def is_snmp_check(check_name):
    return check_name.split(".")[0] in snmp_info


def is_tcp_check(check_name):
    return check_name in check_info \
       and check_name.split(".")[0] not in snmp_info # snmp check basename


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

def is_tcp_host(hostname):
    return in_binary_hostlist(hostname, tcp_hosts)

def is_ping_host(hostname):
    return not is_snmp_host(hostname) and not is_tcp_host(hostname) and not has_piggyback_info(hostname)

def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)

def is_ipv4_host(hostname):
    # Either explicit IPv4 or implicit (when host is not an IPv6 host)
    return "ip-v4" in tags_of_host(hostname) or "ip-v6" not in tags_of_host(hostname)

def is_ipv6_host(hostname):
    return "ip-v6" in tags_of_host(hostname)

def is_ipv6_primary(hostname):
    dual_stack_host = is_ipv4v6_host(hostname)
    return (not dual_stack_host and is_ipv6_host(hostname)) \
            or (dual_stack_host and host_extra_conf(hostname, primary_address_family) == "ipv6")

def is_ipv4v6_host(hostname):
    tags = tags_of_host(hostname)
    return "ip-v6" in tags and "ip-v4" in tags


# Returns a list of all host names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_realhosts():
    return strip_tags(all_hosts)

# Returns a list of all cluster names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_clusters():
    return strip_tags(clusters.keys())

def all_configured_hosts():
    return all_configured_realhosts() + all_configured_clusters()

def all_active_hosts():
    return all_active_realhosts() + all_active_clusters()

def duplicate_hosts():
    # Sanity check for duplicate hostnames
    seen_hostnames = set([])
    duplicates = set([])

    # Only available with CEE
    if "shadow_hosts" in globals():
        shadow_host_entries = shadow_hosts.keys()
    else:
        shadow_host_entries = []

    for hostname in all_active_hosts() + shadow_host_entries:
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)
    return sorted(list(duplicates))


# Returns a list of all host names to be handled by this site
# hosts of other sitest or disabled hosts are excluded
all_hosts_untagged = None
def all_active_realhosts():
    global all_hosts_untagged
    if all_hosts_untagged == None:
        all_hosts_untagged = filter_active_hosts(all_configured_realhosts())
    return all_hosts_untagged

# Returns a list of all cluster host names to be handled by
# this site hosts of other sitest or disabled hosts are excluded
all_clusters_untagged = None
def all_active_clusters():
    global all_clusters_untagged
    if all_clusters_untagged == None:
        all_clusters_untagged = filter_active_hosts(all_configured_clusters())
    return all_clusters_untagged

def filter_active_hosts(hostlist):
    if only_hosts == None and distributed_wato_site == None:
        return hostlist
    elif only_hosts == None:
        return [ hostname for hostname in hostlist
                 if host_is_member_of_site(hostname, distributed_wato_site) ]
    elif distributed_wato_site == None:
        return [ hostname for hostname in hostlist
                 if in_binary_hostlist(hostname, only_hosts) ]
    else:
        site_tag = "site:" + distributed_wato_site
        return [ hostname for hostname in hostlist
                 if in_binary_hostlist(hostname, only_hosts)
                 and host_is_member_of_site(hostname, distributed_wato_site) ]

def host_is_member_of_site(hostname, site):
    for tag in tags_of_host(hostname):
        if tag.startswith("site:"):
            return site == tag[5:]
    # hosts without a site: tag belong to all sites
    return True

def parse_hostname_list(args, with_clusters = True, with_foreign_hosts = False):
    if with_foreign_hosts:
        valid_hosts = all_configured_realhosts()
    else:
        valid_hosts = all_active_realhosts()
    if with_clusters:
        valid_hosts += all_active_clusters()
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
                if hosttags_match_taglist(tags_of_host(hostname), tagspec):
                    hostlist.append(hostname)
                    num_found += 1
            if num_found == 0:
                sys.stderr.write("Hostname or tag specification '%s' does "
                                 "not match any host.\n" % arg)
                sys.exit(1)
    return hostlist

def alias_of(hostname, fallback):
    aliases = host_extra_conf(hostname, extra_host_conf.get("alias", []))
    if len(aliases) == 0:
        if fallback:
            return fallback
        else:
            return hostname
    else:
        return aliases[0]



def hostgroups_of(hostname):
    return host_extra_conf(hostname, host_groups)

def summary_hostgroups_of(hostname):
    return host_extra_conf(hostname, summary_host_groups)

def host_contactgroups_of(hostlist):
    cgrs = []
    for host in hostlist:
        # host_contactgroups may take single values as well as
        # lists as item value. Of all list entries only the first
        # one is used. The single-contact-groups entries are all
        # recognized.
        first_list = True
        for entry in host_extra_conf(host, host_contactgroups):
            if type(entry) == list and first_list:
                cgrs += entry
                first_list = False
            else:
                cgrs.append(entry)
    if monitoring_core == "nagios" and enable_rulebased_notifications:
        cgrs.append("check-mk-notify")
    return list(set(cgrs))


def parents_of(hostname):
    par = host_extra_conf(hostname, parents)
    # Use only those parents which are defined and active in
    # all_hosts.
    used_parents = []
    for p in par:
        ps = p.split(",")
        for pss in ps:
            if pss in all_active_realhosts():
                used_parents.append(pss)
    return used_parents

g_converted_host_rulesets_cache = {}
g_global_caches.append('g_converted_host_rulesets_cache')

def convert_host_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    if len(ruleset) == 1 and ruleset[0] == "":
        sys.stderr.write('WARNING: deprecated entry [ "" ] in host configuration list\n')

    for rule in ruleset:
        item, tags, hostlist, rule_options = parse_host_rule(rule)
        if rule_options.get("disabled"):
            continue

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        new_rules.append((item, all_matching_hosts(tags, hostlist, with_foreign_hosts)))

    return new_rules


def host_extra_conf(hostname, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    try:
        ruleset = g_converted_host_rulesets_cache[cache_id]
    except KeyError:
        ruleset = convert_host_ruleset(ruleset, with_foreign_hosts)
        g_converted_host_rulesets_cache[cache_id] = ruleset

    entries = []
    for item, hostname_list in ruleset:
        if hostname in hostname_list:
            entries.append(item)
    return entries


def parse_host_rule(rule):
    rule, rule_options = get_rule_options(rule)

    num_elements = len(rule)
    if num_elements == 2:
        item, hostlist = rule
        tags = []
    elif num_elements == 3:
        item, tags, hostlist = rule
    else:
        raise MKGeneralException("Invalid entry '%r' in host configuration list: must "
                                 "have 2 or 3 entries" % (rule,))

    return item, tags, hostlist, rule_options


# Needed for agent bakery: Compute ruleset for "generic" host. This
# fictious host has no name and no tags. It matches all rules that
# do not require specific hosts or tags. But it matches rules that
# e.g. except specific hosts or tags (is not, has not set)
def generic_host_extra_conf(ruleset):
    entries = []

    for rule in ruleset:
        item, tags, hostlist, rule_options = parse_host_rule(rule)
        if tags and not hosttags_match_taglist([], tags):
            continue
        if not in_extraconf_hostlist(hostlist, ""):
            continue

        entries.append(item)
    return entries


def host_extra_conf_merged(hostname, conf):
    rule_dict = {}
    for rule in host_extra_conf(hostname, conf):
        for key, value in rule.items():
            rule_dict.setdefault(key, value)
    return rule_dict


def in_binary_hostlist(hostname, conf):
    # if we have just a list of strings just take it as list of hostnames
    if conf and type(conf[0]) == str:
        return hostname in conf

    for entry in conf:
        entry, rule_options = get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        try:
            # Negation via 'NEGATE'
            if entry[0] == NEGATE:
                entry = entry[1:]
                negate = True
            else:
                negate = False
            # entry should be one-tuple or two-tuple. Tuple's elements are
            # lists of strings. User might forget comma in one tuple. Then the
            # entry is the list itself.
            if type(entry) == list:
                hostlist = entry
                tags = []
            else:
                if len(entry) == 1: # 1-Tuple with list of hosts
                    hostlist = entry[0]
                    tags = []
                else:
                    tags, hostlist = entry

            if hosttags_match_taglist(tags_of_host(hostname), tags) and \
                   in_extraconf_hostlist(hostlist, hostname):
                return not negate

        except:
            MKGeneralException("Invalid entry '%r' in host configuration list: "
                               "must be tupel with 1 or 2 entries" % (entry,))

    return False


# Pick out the last element of an entry if it is a dictionary.
# This is a new feature (1.2.0p3) that allows to add options
# to rules. Currently only the option "disabled" is being
# honored. WATO also uses the option "comment".
def get_rule_options(entry):
    if type(entry[-1]) == dict:
        return entry[:-1], entry[-1]
    else:
        return entry, {}


def is_regex(pattern):
    for c in pattern:
        if c in '.?*+^$|[](){}\\':
            return True
    return False


# Converts a regex pattern which is used to e.g. match services within Check_MK
# to a function reference to a matching function which takes one parameter to
# perform the matching and returns a two item tuple where the first element
# tells wether or not the pattern is negated and the second element the outcome
# of the match.
# This function tries to parse the pattern and return different kind of matching
# functions which can then be performed faster than just using the regex match.
def convert_pattern(pattern):
    def is_infix_string_search(pattern):
        return pattern.startswith('.*') and not is_regex(pattern[2:])

    def is_exact_match(pattern):
        return pattern[-1] == '$' and not is_regex(pattern[:-1])

    def is_prefix_match(pattern):
        return pattern[-2:] == '.*' and not is_regex(pattern[:-2])

    if pattern == '':
        return False, lambda txt: True # empty patterns match always

    negate, pattern = parse_negated(pattern)

    if is_exact_match(pattern):
        # Exact string match
        return negate, lambda txt: pattern[:-1] == txt

    elif is_infix_string_search(pattern):
        # Using regex to search a substring within text
        return negate, lambda txt: pattern[2:] in txt

    elif is_prefix_match(pattern):
        # prefix match with tailing .*
        pattern = pattern[:-2]
        return negate, lambda txt: txt[:len(pattern)] == pattern

    elif is_regex(pattern):
        # Non specific regex. Use real prefix regex matching
        return negate, lambda txt: regex(pattern).match(txt) != None

    else:
        # prefix match without any regex chars
        return negate, lambda txt: txt[:len(pattern)] == pattern


def convert_pattern_list(patterns):
    return tuple([ convert_pattern(p) for p in patterns ])

g_hostlist_match_cache = {}
g_global_caches.append('g_hostlist_match_cache')

def all_matching_hosts(tags, hostlist, with_foreign_hosts):
    cache_id = tuple(tags), tuple(hostlist), with_foreign_hosts
    try:
        return g_hostlist_match_cache[cache_id]
    except KeyError:
        pass

    if with_foreign_hosts:
        valid_hosts = all_configured_hosts()
    else:
        valid_hosts = all_active_hosts()

    matching = set([])
    for hostname in valid_hosts:
        # When no tag matching is requested, do not filter by tags. Accept all hosts
        # and filter only by hostlist
        if in_extraconf_hostlist(hostlist, hostname) and \
           (not tags or hosttags_match_taglist(tags_of_host(hostname), tags)):
           matching.add(hostname)

    g_hostlist_match_cache[cache_id] = matching
    return matching


g_converted_service_rulesets_cache = {}
g_global_caches.append('g_converted_service_rulesets_cache')

def convert_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        rule, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        num_elements = len(rule)
        if num_elements == 3:
            item, hostlist, servlist = rule
            tags = []
        elif num_elements == 4:
            item, tags, hostlist, servlist = rule
        else:
            raise MKGeneralException("Invalid rule '%r' in service configuration "
                                     "list: must have 3 or 4 elements" % (rule,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)

        # And now preprocess the configured patterns in the servlist
        new_rules.append((item, hosts, convert_pattern_list(servlist)))

    return new_rules


g_extraconf_servicelist_cache = {}
g_global_caches.append('g_extraconf_servicelist_cache')

# Compute outcome of a service rule set that has an item
def service_extra_conf(hostname, service, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    try:
        ruleset = g_converted_service_rulesets_cache[cache_id]
    except KeyError:
        ruleset = convert_service_ruleset(ruleset, with_foreign_hosts)
        g_converted_service_rulesets_cache[cache_id] = ruleset

    entries = []
    for item, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service
            try:
                match = g_extraconf_servicelist_cache[cache_id]
            except:
                match = in_servicematcher_list(service_matchers, service)
                g_extraconf_servicelist_cache[cache_id] = match

            if match:
                entries.append(item)
    return entries


def convert_boolean_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        entry, rule_options = get_rule_options(rule)
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
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)
        new_rules.append((negate, hosts, convert_pattern_list(servlist)))

    return new_rules


# Compute outcome of a service rule set that just say yes/no
def in_boolean_serviceconf_list(hostname, service_description, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    try:
        ruleset = g_converted_service_rulesets_cache[cache_id]
    except KeyError:
        ruleset = convert_boolean_service_ruleset(ruleset, with_foreign_hosts)
        g_converted_service_rulesets_cache[cache_id] = ruleset

    for negate, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service_description
            try:
                match = g_extraconf_servicelist_cache[cache_id]
            except:
                match = in_servicematcher_list(service_matchers, service_description)
                g_extraconf_servicelist_cache[cache_id] = match

            if match:
                return not negate
    return False # no match. Do not ignore


# Entries in list are hostnames that must equal the hostname.
# Expressions beginning with ! are negated: if they match,
# the item is excluded from the list. Expressions beginning
# withy ~ are treated as Regular Expression. Also the three
# special tags '@all', '@clusters', '@physical' are allowed.
def in_extraconf_hostlist(hostlist, hostname):

    # Migration help: print error if old format appears in config file
    # FIXME: When can this be removed?
    try:
        if hostlist[0] == "":
            raise MKGeneralException('Invalid empty entry [ "" ] in configuration')
    except IndexError:
        pass # Empty list, no problem.

    for hostentry in hostlist:
        if hostentry == '':
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        negate = False
        use_regex = False
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            ic = is_cluster(hostname)
            if hostentry == '@cluster' and ic:
                return True
            elif hostentry == '@physical' and not ic:
                return True

        # Allow negation of hostentry with prefix '!'
        else:
            if hostentry[0] == '!':
                hostentry = hostentry[1:]
                negate = True
            # Allow regex with prefix '~'
            if hostentry[0] == '~':
                hostentry = hostentry[1:]
                use_regex = True

        hostentry = hostentry
        try:
            if not use_regex and hostname == hostentry:
                return not negate
            # Handle Regex. Note: hostname == True -> generic unknown host
            elif use_regex and hostname != True:
                if regex(hostentry).match(hostname) != None:
                    return not negate
        except MKGeneralException:
            if opt_debug:
                raise

    return False

# Slow variant of checking wether a service is matched by a list
# of regexes - used e.g. by cmk --notify
def in_extraconf_servicelist(servicelist, service):
    return in_servicematcher_list(convert_pattern_list(servicelist), service)


def in_servicematcher_list(service_matchers, item):
    for negate, func in service_matchers:
        result = func(item)
        if result:
            return not negate

    # no match in list -> negative answer
    return False

def extra_host_conf_of(hostname):
    return extra_conf_of(extra_host_conf, hostname, None)

def extra_summary_host_conf_of(hostname):
    return extra_conf_of(extra_summary_host_conf, hostname, None)

# Collect all extra configuration data for a service
def extra_service_conf_of(hostname, description):
    global contactgroups_to_define
    global servicegroups_to_define
    conf = ""

    # Contact groups
    sercgr = service_extra_conf(hostname, description, service_contactgroups)
    contactgroups_to_define.update(sercgr)
    if len(sercgr) > 0:
        if enable_rulebased_notifications:
            sercgr.append("check-mk-notify") # not nessary if not explicit groups defined
        conf += "  contact_groups\t\t" + ",".join(sercgr) + "\n"

    sergr = service_extra_conf(hostname, description, service_groups)
    if len(sergr) > 0:
        conf += "  service_groups\t\t" + ",".join(sergr) + "\n"
        if define_servicegroups:
            servicegroups_to_define.update(sergr)
    conf += extra_conf_of(extra_service_conf, hostname, description)
    return conf.encode("utf-8")

def extra_summary_service_conf_of(hostname, description):
    return extra_conf_of(extra_summary_service_conf, hostname, description)

def extra_conf_of(confdict, hostname, service):
    result = ""
    for key, conflist in confdict.items():
        if service != None:
            values = service_extra_conf(hostname, service, conflist)
        else:
            values = host_extra_conf(hostname, conflist)
        if len(values) > 0:
            format = "  %-29s %s\n"
            result += format % (key, values[0])
    return result

def autodetect_plugin(command_line):
    plugin_name = command_line.split()[0]
    if command_line[0] not in [ '$', '/' ]:
        try:
            for dir in [ "/local", "" ]:
                path = omd_root + dir + "/lib/nagios/plugins/"
                if os.path.exists(path + plugin_name):
                    command_line = path + command_line
                    break
        except:
            pass
    return command_line

def host_check_command(hostname, ip, is_clust):
    # Check dedicated host check command
    values = host_extra_conf(hostname, host_check_commands)
    if values:
        value = values[0]
    elif monitoring_core == "cmc":
        value = "smart"
    else:
        value = "ping"

    if monitoring_core != "cmc" and value == "smart":
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
        if monitoring_core == "cmc":
            return "check-mk-host-service!" + service
        command = "check-mk-host-custom-%d" % (len(hostcheck_commands_to_define) + 1)
        hostcheck_commands_to_define.append((command,
           'echo "$SERVICEOUTPUT:%s:%s$" && exit $SERVICESTATEID:%s:%s$' % (hostname, service, hostname, service)))
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
        return list(set(host_extra_conf(hostname, host_icons_and_actions)))
    else:
        actions = set(service_extra_conf(hostname, svcdesc, service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if checkname:
            checkgroup = check_info[checkname]["group"]
            if checkgroup in [ 'ps', 'services' ] and type(params) == dict:
                icon = params.get('icon')
                if icon:
                    actions.add(icon)

        return list(actions)


def check_icmp_arguments_of(hostname, add_defaults=True, family=None):
    values = host_extra_conf(hostname, ping_levels)
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
#   .--Host tags-----------------------------------------------------------.
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with host tags                         |
#   '----------------------------------------------------------------------'

def parse_negated(pattern):
    # Allow negation of pattern with prefix '!'
    try:
        negate = pattern[0] == '!'
        if negate:
            pattern = pattern[1:]
    except IndexError:
        negate = False
    return negate, pattern

def strip_tags(tagged_hostlist):
    return map(lambda h: h.split('|', 1)[0], tagged_hostlist)

def tags_of_host(hostname):
    try:
        return hosttags[hostname]
    except KeyError:
        return []

hosttags = {}
def collect_hosttags():
    for taggedhost in all_hosts + clusters.keys():
        parts = taggedhost.split("|")
        hosttags[parts[0]] = sorted(parts[1:])


g_hosttag_taglist_cache = {}
g_global_caches.append('g_hosttag_taglist_cache')

# Check if a host fulfills the requirements of a tags
# list. The host must have all tags in the list, except
# for those negated with '!'. Those the host must *not* have!
# New in 1.1.13: a trailing + means a prefix match
def hosttags_match_taglist(hosttags, required_tags):
    try:
        cache_id = tuple(hosttags), tuple(required_tags)
        return g_hosttag_taglist_cache[cache_id]
    except KeyError:
        pass

    for tag in required_tags:
        negate, tag = parse_negated(tag)
        if tag and tag[-1] == '+':
            tag = tag[:-1]
            matches = False
            for t in hosttags:
                if t.startswith(tag):
                    matches = True
                    break

        else:
            matches = tag in hosttags

        if matches == negate:
            g_hosttag_taglist_cache[cache_id] = False
            return False

    g_hosttag_taglist_cache[cache_id] = True
    return True

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
    if not service_aggregations:
        return False

    # host might by explicitly configured as not aggregated
    if in_binary_hostlist(hostname, non_aggregated_hosts):
        return False

    # convert into host_conf_list suitable for host_extra_conf()
    host_conf_list = [ entry[:-1] for entry in service_aggregations ]
    is_aggr = len(host_extra_conf(hostname, host_conf_list)) > 0
    return is_aggr

# Determines the aggregated service name for a given
# host and service description. Returns "" if the service
# is not aggregated
def aggregated_service_name(hostname, servicedesc):
    if not service_aggregations:
        return ""

    for entry in service_aggregations:
        if len(entry) == 3:
            aggrname, hostlist, pattern = entry
            tags = []
        elif len(entry) == 4:
            aggrname, tags, hostlist, pattern = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service_aggregations: must have 3 or 4 entries" % entry)

        if len(hostlist) == 1 and hostlist[0] == "":
            sys.stderr.write('WARNING: deprecated hostlist [ "" ] in service_aggregations. Please use all_hosts instead\n')

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
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

def plugin_pathnames_in_directory(path):
    if path and os.path.exists(path):
        return sorted([
            path + "/" + f
            for f in os.listdir(path)
            if not f.startswith(".")
        ])
    else:
        return []

def check_period_of(hostname, service):
    periods = service_extra_conf(hostname, service, check_periods)
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
    for match, minutes in host_extra_conf(hostname, snmp_check_interval):
        if match is None or match == checkname:
            return minutes # use first match

def agent_target_version(hostname):
    agent_target_versions = host_extra_conf(hostname, check_mk_agent_target_versions)
    if len(agent_target_versions) > 0:
        spec = agent_target_versions[0]
        if spec == "ignore":
            return None
        elif spec == "site":
            return check_mk_version
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
    global check_max_cachefile_age, cluster_max_cachefile_age, inventory_max_cachefile_age
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if check_max_cachefile_age != 1000000000:
        orig_check_max_cachefile_age     = check_max_cachefile_age
        orig_cluster_max_cachefile_age   = cluster_max_cachefile_age
        orig_inventory_max_cachefile_age = inventory_max_cachefile_age

    check_max_cachefile_age     = 1000000000
    cluster_max_cachefile_age   = 1000000000
    inventory_max_cachefile_age = 1000000000


def restore_original_agent_caching_usage():
    global check_max_cachefile_age, cluster_max_cachefile_age, inventory_max_cachefile_age
    global orig_check_max_cachefile_age, orig_cluster_max_cachefile_age, \
           orig_inventory_max_cachefile_age

    if orig_check_max_cachefile_age != None:
        check_max_cachefile_age     = orig_check_max_cachefile_age
        cluster_max_cachefile_age   = orig_cluster_max_cachefile_age
        inventory_max_cachefile_age = orig_inventory_max_cachefile_age

        orig_check_max_cachefile_age     = None
        orig_cluster_max_cachefile_age   = None
        orig_inventory_max_cachefile_age = None


def schedule_inventory_check(hostname):
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(livestatus_unix_socket)
        now = int(time.time())
        if 'cmk-inventory' in use_new_descriptions_for:
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK Discovery;%d" % (hostname, now)
        else:
            # TODO: Remove this old name handling one day
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK inventory;%d" % (hostname, now)

        # Ignore missing check and avoid warning in cmc.log
        if monitoring_core == "cmc":
            command += ";TRY"

        s.send("COMMAND [%d] %s\n" % (now, command))
    except Exception, e:
        if opt_debug:
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
    try:
        return explicit_snmp_communities[hostname]
    except KeyError:
        pass

    communities = host_extra_conf(hostname, snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community

def get_snmp_character_encoding(hostname):
    entries = host_extra_conf(hostname, snmp_character_encodings)
    if len(entries) > 0:
        return entries[0]

def is_snmpv3_host(hostname):
    return type(snmp_credentials_of(hostname)) == tuple

def is_snmp_host(hostname):
    return in_binary_hostlist(hostname, snmp_hosts)

def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return in_binary_hostlist(hostname, bulkwalk_hosts)
    else:
        return False

def is_snmpv2c_host(hostname):
    return is_bulkwalk_host(hostname) or \
        in_binary_hostlist(hostname, snmpv2c_hosts)

def is_usewalk_host(hostname):
    return in_binary_hostlist(hostname, usewalk_hosts)


def is_inline_snmp_host(hostname):
    return has_inline_snmp and use_inline_snmp \
           and not in_binary_hostlist(hostname, non_inline_snmp_hosts)


def snmp_timing_of(hostname):
    timing = host_extra_conf(hostname, snmp_timing)
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
    return snmp_base_command('walk', hostname) + " -Cc"

def snmp_base_command(what, hostname):
    # if the credentials are a string, we use that as community,
    # if it is a four-tuple, we use it as V3 auth parameters:
    # (1) security level (-l)
    # (2) auth protocol (-a, e.g. 'md5')
    # (3) security name (-u)
    # (4) auth password (-A)
    # And if it is a six-tuple, it has the following additional arguments:
    # (5) privacy protocol (DES|AES) (-x)
    # (6) privacy protocol pass phrase (-X)

    credentials = snmp_credentials_of(hostname)
    if what == 'get':
        command = 'snmpget'
    elif what == 'getnext':
        command = 'snmpgetnext -Cf'
    elif is_bulkwalk_host(hostname):
        command = 'snmpbulkwalk'
    else:
        command = 'snmpwalk'

    # Handle V1 and V2C
    if type(credentials) in [ str, unicode ]:
        if is_bulkwalk_host(hostname):
            options = '-v2c'
        else:
            if what == 'walk':
                command = 'snmpwalk'
            if is_snmpv2c_host(hostname):
                options = '-v2c'
            else:
                options = '-v1'
        options += " -c '%s'" % credentials

        # Handle V3
    else:
        if len(credentials) == 6:
           options = "-v3 -l '%s' -a '%s' -u '%s' -A '%s' -x '%s' -X '%s'" % tuple(credentials)
        elif len(credentials) == 4:
           options = "-v3 -l '%s' -a '%s' -u '%s' -A '%s'" % tuple(credentials)
        elif len(credentials) == 2:
           options = "-v3 -l '%s' -u '%s'" % tuple(credentials)
        else:
            raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be string, 2-tuple, 4-tuple or 6-tuple" % (credentials, hostname))

    # Do not load *any* MIB files. This save lot's of CPU.
    options += " -m '' -M ''"

    # Configuration of timing and retries
    settings = snmp_timing_of(hostname)
    if "timeout" in settings:
        options += " -t %0.2f" % settings["timeout"]
    if "retries" in settings:
        options += " -r %d" % settings["retries"]

    return command + ' ' + options

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
              " -On -OQ -Oe -Ot %s%s%s %s" % (protospec, ipaddress, portspec, oid_prefix)

    if opt_debug:
        sys.stdout.write("Running '%s'\n" % command)

    snmp_process = subprocess.Popen(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    exitstatus = snmp_process.wait()
    if exitstatus:
        if opt_verbose:
            sys.stderr.write(tty_red + tty_bold + "ERROR: " + tty_normal + "SNMP error\n")
            sys.stderr.write(snmp_process.stderr.read())
        return None

    line = snmp_process.stdout.readline().strip()
    if not line:
        if opt_debug:
            sys.stdout.write("Error in response to snmpget.\n")
        return None

    item, value = line.split("=", 1)
    value = value.strip()
    if opt_debug:
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
        if opt_debug:
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        else:
            oid = '.' + oid

    clear_other_hosts_oid_cache(hostname)

    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    vverbose("       Getting OID %s: " % oid)
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
                value = inline_snmp_get_oid(hostname, oid)
            else:
                value = snmp_get_oid(hostname, ipaddress, oid)
        except:
            if opt_debug:
                raise
            value = None

    if value != None:
        vverbose("%s%s%s%s\n" % (tty_bold, tty_green, value, tty_normal))
    else:
        vverbose("failed.\n")

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


# Checks whether or not the given host is a cluster host
def is_cluster(hostname):
    # all_configured_clusters() needs to be used, because this function affects
    # the agent bakery, which needs all configured hosts instead of just the hosts
    # of this site
    return hostname in all_configured_clusters()

# If host is node of one or more clusters, return a list of the cluster host names.
# If not, return an empty list.
def clusters_of(hostname):
    return [ c.split('|', 1)[0] for c,n in clusters.items() if hostname in n ]

# Determine weather a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    the_clusters = clusters_of(hostname)
    if not the_clusters:
        return hostname

    cluster_mapping = service_extra_conf(hostname, servicedesc, clustered_services_mapping)
    for cluster in cluster_mapping:
        # Check if the host is in this cluster
        if cluster in the_clusters:
            return cluster

    # 1. New style: explicitly assigned services
    for cluster, conf in clustered_services_of.items():
        nodes = nodes_of(cluster)
        if not nodes:
            raise MKGeneralException("Invalid entry clustered_services_of['%s']: %s is not a cluster." %
                   (cluster, cluster))
        if hostname in nodes and \
            in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
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
    global g_singlehost_checks
    global g_multihost_checks

    if is_ping_host(hostname):
        skip_autochecks = True

    # speed up multiple lookup of same host
    if not skip_autochecks and use_cache and hostname in g_check_table_cache:
        if remove_duplicates and is_dual_host(hostname):
            return remove_duplicate_checks(g_check_table_cache[hostname])
        else:
            return g_check_table_cache[hostname]

    check_table = {}

    # First time? Split up all checks in single and
    # multi-host-checks
    if g_singlehost_checks == None:
        g_singlehost_checks = {}
        g_multihost_checks = []
        for entry in checks:
            if len(entry) == 4 and type(entry[0]) == str:
                g_singlehost_checks.setdefault(entry[0], []).append(entry)
            else:
                g_multihost_checks.append(entry)

    hosttags = tags_of_host(hostname)

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

        # Skip SNMP checks for non SNMP hosts (might have been discovered before with other
        # agent setting. Remove them without rediscovery). Same for agent based checks.
        if not is_snmp_host(hostname) and is_snmp_check(checkname):
            return
        if not is_tcp_host(hostname) and not has_piggyback_info(hostname) \
           and is_tcp_check(checkname):
            return

        if hosttags_match_taglist(hosttags, tags) and \
               in_extraconf_hostlist(hostlist, hostname):
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

    for entry in g_singlehost_checks.get(hostname, []):
        handle_entry(entry)

    for entry in g_multihost_checks:
        handle_entry(entry)

    # Now add checks a cluster might receive from its nodes
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            node_checks = g_singlehost_checks.get(node, [])
            if not skip_autochecks:
                node_checks = node_checks + read_autochecks_of(node, world)
            for entry in node_checks:
                if len(entry) == 4:
                    entry = entry[1:] # drop hostname from g_singlehost_checks
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
        g_check_table_cache[hostname] = check_table

    if remove_duplicates:
        return remove_duplicate_checks(check_table)
    else:
        return check_table


def get_precompiled_check_table(hostname, remove_duplicates=True, world="config"):
    host_checks = get_sorted_check_table(hostname, remove_duplicates, world)
    precomp_table = []
    for check_type, item, params, description, deps in host_checks:
        # make these globals available to the precompile function
        global g_service_description, g_check_type, g_checked_item
        g_service_description = description
        g_check_type = check_type
        g_checked_item = item

        aggr_name = aggregated_service_name(hostname, description)
        params = get_precompiled_check_parameters(hostname, item, params, check_type)
        precomp_table.append((check_type, item, params, description, aggr_name)) # deps not needed while checking
    return precomp_table


def get_precompiled_check_parameters(hostname, item, params, check_type):
    precomp_func = precompile_params.get(check_type)
    if precomp_func:
        return precomp_func(hostname, item, params)
    else:
        return params


# Return a list of services this services depends upon
def service_deps(hostname, servicedesc):
    deps = []
    for entry in service_dependencies:
        entry, rule_options = get_rule_options(entry)
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

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
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



# Determine, which program to call to get data. Should
# be None in most cases -> to TCP connect on port 6556

def get_datasource_program(hostname, ipaddress):
    special_agents_dir = agents_dir + "/special"

    # First check WATO-style special_agent rules
    for agentname, ruleset in special_agents.items():
        params = host_extra_conf(hostname, ruleset)
        if params: # rule match!
            # Create command line using the special_agent_info
            cmd_arguments = special_agent_info[agentname](params[0], hostname, ipaddress)
            if local_special_agents_dir and \
                os.path.exists(local_special_agents_dir + "/agent_" + agentname):
                path = local_special_agents_dir + "/agent_" + agentname
            else:
                path = special_agents_dir + "/agent_" + agentname
            return path + " " + cmd_arguments

    programs = host_extra_conf(hostname, datasource_programs)
    if len(programs) == 0:
        return None
    else:
        return programs[0].replace("<IP>", ipaddress).replace("<HOST>", hostname)

# Variables needed during the renaming of hosts (see automation.py)
ignore_ip_lookup_failures = False
g_failed_ip_lookups = []
g_dns_cache = {}
g_global_caches.append('g_dns_cache')

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
    elif simulation_mode or opt_use_snmp_walk or \
         (is_usewalk_host(hostname) and is_snmp_host(hostname)):
        if family == 4:
            return "127.0.0.1"
        else:
            return "::1"

    # Now check, if IP address is hard coded by the user
    if family == 4:
        ipa = ipaddresses.get(hostname)
    else:
        ipa = ipv6addresses.get(hostname)
    if ipa:
        return ipa

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if in_binary_hostlist(hostname, dyndns_hosts):
        return hostname

    # Address has already been resolved in prior call to this function?
    if (hostname, family) in g_dns_cache:
        return g_dns_cache[(hostname, family)]

    # Prepare file based fall-back DNS cache in case resolution fails
    init_ip_lookup_cache()

    cached_ip = g_ip_lookup_cache.get((hostname, family))
    if cached_ip and use_dns_cache:
        g_dns_cache[(hostname, family)] = cached_ip
        return cached_ip

    # Now do the actual DNS lookup
    try:
        ipa = socket.getaddrinfo(hostname, None, family == 4 and socket.AF_INET or socket.AF_INET6)[0][4][0]

        # Update our cached address if that has changed or was missing
        if ipa != cached_ip:
            if opt_verbose:
                print "Updating IPv%d DNS cache for %s: %s" % (family, hostname, ipa)
            g_ip_lookup_cache[(hostname, family)] = ipa
            write_ip_lookup_cache()

        g_dns_cache[(hostname, family)] = ipa # Update in-memory-cache
        return ipa

    except:
        # DNS failed. Use cached IP address if present, even if caching
        # is disabled.
        if cached_ip:
            g_dns_cache[(hostname, family)] = cached_ip
            return cached_ip
        else:
            g_dns_cache[(hostname, family)] = None
            raise

def init_ip_lookup_cache():
    global g_ip_lookup_cache
    if g_ip_lookup_cache is None:
        try:
            g_ip_lookup_cache = eval(file(var_dir + '/ipaddresses.cache').read())

            # be compatible to old caches which were created by Check_MK without IPv6 support
            if g_ip_lookup_cache and type(g_ip_lookup_cache.keys()[0]) != tuple:
                new_cache = {}
                for key, val in g_ip_lookup_cache.items():
                    new_cache[(key, 4)] = val
                g_ip_lookup_cache = new_cache
        except:
            g_ip_lookup_cache = {}


def write_ip_lookup_cache():
    suffix = "." + str(os.getpid())
    file(var_dir + '/ipaddresses.cache' + suffix, 'w').write(repr(g_ip_lookup_cache))
    os.rename(var_dir + '/ipaddresses.cache' + suffix, var_dir + '/ipaddresses.cache')


def do_update_dns_cache():
    # Temporarily disable *use* of cache, we want to force an update
    global use_dns_cache
    use_dns_cache = False
    updated = 0
    failed = []

    verbose("Updating DNS cache...\n")
    for hostname in all_active_hosts():
        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        for family in [ 4, 6]:
            if (family == 4 and is_ipv4_host(hostname)) \
               or (family == 6 and is_ipv6_host(hostname)):
                verbose("%s (IPv%d)..." % (hostname, family))
                try:
                    if family == 4:
                        ip = lookup_ipv4_address(hostname)
                    else:
                        ip = lookup_ipv6_address(hostname)

                    verbose("%s\n" % ip)
                    updated += 1
                except Exception, e:
                    failed.append(hostname)
                    verbose("lookup failed: %s\n" % e)
                    if opt_debug:
                        raise
                    continue

    return updated, failed


def agent_port_of(hostname):
    ports = host_extra_conf(hostname, agent_ports)
    if len(ports) == 0:
        return agent_port
    else:
        return ports[0]

def snmp_port_of(hostname):
    ports = host_extra_conf(hostname, snmp_ports)
    if len(ports) == 0:
        return None # do not specify a port, use default
    else:
        return ports[0]

def exit_code_spec(hostname):
    spec = {}
    specs = host_extra_conf(hostname, check_mk_exit_status)
    for entry in specs[::-1]:
        spec.update(entry)
    return spec


# Remove illegal characters from a service description
def sanitize_service_description(descr):
    return "".join([ c for c in descr if c not in nagios_illegal_chars ]).rstrip("\\")


def service_description(hostname, check_type, item):
    if check_type not in check_info:
        if item:
            return "Unimplemented check %s / %s" % (check_type, item)
        else:
            return "Unimplemented check %s" % check_type

    # use user-supplied service description, if available
    add_item = True
    descr_format = service_descriptions.get(check_type)
    if not descr_format:
        # handle renaming for backward compatibility
        if check_type in old_service_descriptions and \
            check_type not in use_new_descriptions_for:

            # Can be a fucntion to generate the old description more flexible.
            old_descr = old_service_descriptions[check_type]
            if callable(old_descr):
                add_item, descr_format = old_descr(item)
            else:
                descr_format = old_descr

        else:
            descr_format = check_info[check_type]["service_description"]

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
    rules = host_extra_conf(hostname, piggyback_translation)
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
service_service_levels = None
host_service_levels = None
derived_config_variable_names = [ "hosttags", "service_service_levels", "host_service_levels" ]

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
    "host_attributes",
    "all_hosts_untagged",
    "all_clusters_untagged",
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

    filepath = var_dir + "/core/config.mk"
    out = file(filepath + ".new", "w")
    out.write("#!/usr/bin/python\n"
              "# encoding: utf-8\n"
              "# Created by Check_MK. Dump of the currently active configuration\n\n")




    # These functions purpose is to filter out hosts which are monitored on different sites
    active_hosts    = all_active_hosts()
    active_clusters = all_active_clusters()
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
        "explicit_snmp_communities": filter_hostname_in_dict,
        "hosttags"                 : filter_hostname_in_dict
    }

    for varname in list(config_variable_names) + derived_config_variable_names:
        if varname not in skipped_config_variable_names:
            val = globals()[varname]
            if packable(varname, val):
                if varname in filter_var_functions:
                    val = filter_var_functions[varname](val)
                out.write("\n%s = %r\n" % (varname, val))

    for varname, factory_setting in factory_settings.items():
        if varname in globals():
            out.write("\n%s = %r\n" % (varname, globals()[varname]))
        else: # remove explicit setting from previous packed config!
            out.write("\nif %r in globals():\n    del %s\n" % (varname, varname))

    out.close()
    os.rename(filepath + ".new", filepath)

def pack_autochecks():
    dstpath = var_dir + "/core/autochecks"
    if not os.path.exists(dstpath):
        os.makedirs(dstpath)
    srcpath = autochecksdir
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

def read_packed_config():
    filepath = var_dir + "/core/config.mk"
    execfile(filepath, globals())

#.
#   .--Man-Pages-----------------------------------------------------------.
#   |         __  __                   ____                                |
#   |        |  \/  | __ _ _ __       |  _ \ __ _  __ _  ___  ___          |
#   |        | |\/| |/ _` | '_ \ _____| |_) / _` |/ _` |/ _ \/ __|         |
#   |        | |  | | (_| | | | |_____|  __/ (_| | (_| |  __/\__ \         |
#   |        |_|  |_|\__,_|_| |_|     |_|   \__,_|\__, |\___||___/         |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   | Each Check has a man page. Here is that code for displaying that in- |
#   | line documentation and also some code for outputting it in a format  |
#   | that is used by the official Check_MK documentation ("nowiki").      |
#   '----------------------------------------------------------------------'

def get_tty_size():
    import termios, struct
    try:
        ws = struct.pack("HHHH", 0, 0, 0, 0)
        ws = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns, x, y = struct.unpack("HHHH", ws)
        if lines > 0 and columns > 0:
            return lines, columns
    except:
        pass
    return (24, 80)


def all_manuals():
    entries = dict([(fn, check_manpages_dir + "/" + fn) for fn in os.listdir(check_manpages_dir)])
    if local_check_manpages_dir and os.path.exists(local_check_manpages_dir):
        entries.update(dict([(fn, local_check_manpages_dir + "/" + fn)
                for fn in os.listdir(local_check_manpages_dir)]))
    return entries

def list_all_manuals():
    table = []
    for filename, path in all_manuals().items():
        if filename.endswith("~"):
            continue

        try:
            for line in file(path):
                if line.startswith("title:"):
                    table.append((filename, line.split(":", 1)[1].strip()))
        except:
            pass

    table.sort()
    print_table(['Check type', 'Title'], [tty_bold, tty_normal], table)


def read_manpage_catalog():
    load_module("catalog")
    global g_manpage_catalog
    g_manpage_catalog = {}
    for checkname, path in all_manuals().items():
        # Skip .* file (.f12)
        a, filename = os.path.split(path)
        if filename.startswith("."):
            continue
        try:
            parsed = parse_man_header(checkname, path)
        except Exception, e:
            if opt_debug:
                raise
            parsed = create_fallback_manpage(checkname, path, e)

        if "catalog" in parsed:
            cat = parsed["catalog"]
        else:
            cat = [ "unsorted" ]

        if cat[0] == "os":
            for agent in parsed["agents"]:
                acat = [cat[0]] + [agent] + cat[1:]
                g_manpage_catalog.setdefault(tuple(acat), []).append(parsed)
        else:
            g_manpage_catalog.setdefault(tuple(cat), []).append(parsed)


def manpage_browser(cat = ()):
    read_manpage_catalog()
    entries = []
    subtrees = set([])
    for c, e in g_manpage_catalog.items():
        if c[:len(cat)] == cat:
            if len(c) > len(cat):
                subtrees.add(c[len(cat)])
            else: # leaf node
                entries = e
                break

    if entries and subtrees:
        sys.stderr.write("ERROR: Catalog path %s contains man pages and subfolders.\n" % ("/".join(cat)))
    if entries:
        manpage_browse_entries(cat, entries)
    elif subtrees:
        manpage_browser_folder(cat, subtrees)


def manpage_num_entries(cat):
    num = 0
    for c, e in g_manpage_catalog.items():
        if c[:len(cat)] == cat:
            num += len(e)
    return num


def manpage_browser_folder(cat, subtrees):
    titles = []
    for e in subtrees:
        title = manpage_catalog_titles.get(e,e)
        count = manpage_num_entries(cat + (e,))
        if count:
            title += " (%d)" % count
        titles.append((title, e))
    titles.sort()
    choices = [ (str(n+1), t[0]) for n,t in enumerate(titles) ]

    while True:
        x = dialog_menu("Man Page Browser", manpage_display_header(cat), choices, "0", "Enter", cat and "Back" or "Quit")
        if x[0] == True:
            index = int(x[1])
            subcat = titles[index-1][1]
            manpage_browser(cat + (subcat,))
        else:
            break


def manpage_browse_entries(cat, entries):
    checks = []
    for e in entries:
        checks.append((e["title"], e["name"]))
    checks.sort()
    choices = [ (str(n+1), c[0]) for n,c in enumerate(checks) ]
    while True:
        x = dialog_menu("Man Page Browser", manpage_display_header(cat), choices, "0", "Show Manpage", "Back")
        if x[0] == True:
            index = int(x[1])-1
            checkname = checks[index][1]
            show_check_manual(checkname)
        else:
            break


def manpage_display_header(cat):
    return " -> ".join([manpage_catalog_titles.get(e,e) for e in cat ])


def run_dialog(args):
    env = {
        "TERM": os.getenv("TERM", "linux"),
        "LANG": "de_DE.UTF-8"
    }
    p = subprocess.Popen(["dialog", "--shadow"] + args, env = env, stderr = subprocess.PIPE)
    response = p.stderr.read()
    return 0 == os.waitpid(p.pid, 0)[1], response


def dialog_menu(title, text, choices, defvalue, oktext, canceltext):
    args = [ "--ok-label", oktext, "--cancel-label", canceltext ]
    if defvalue != None:
        args += [ "--default-item", defvalue ]
    args += [ "--title", title, "--menu", text, "0", "0", "0" ] # "20", "60", "17" ]
    for text, value in choices:
        args += [ text, value ]
    return run_dialog(args)


def create_fallback_manpage(checkname, path, error_message):
    return {
        "name"         : checkname,
        "path"         : path,
        "description"  : file(path).read().strip(),
        "title"        : "%s: Cannot parse man page: %s" % (checkname, error_message),
        "agents"       : "",
        "license"      : "unknown",
        "distribution" : "unknown",
        "catalog"      : [ "generic" ],
    }


def parse_man_header(checkname, path):
    parsed = {}
    parsed["name"] = checkname
    parsed["path"] = path
    key = None
    lineno = 0
    for line in file(path):
        line = line.rstrip()
        lineno += 1
        try:
            if not line:
                parsed[key] += "\n\n"
            elif line[0] == ' ':
                parsed[key] += "\n" + line.lstrip()
            elif line[0] == '[':
                break # End of header
            else:
                key, rest = line.split(":", 1)
                parsed[key] = rest.lstrip()
        except Exception, e:
            if opt_debug:
                raise
            sys.stderr.write("Invalid line %d in man page %s\n%s" % (
                    lineno, path, line))
            break

    # verify mandatory keys. FIXME: This list may be incomplete
    for key in [ "title", "agents", "license", "distribution", "description", ]:
        if key not in parsed:
            raise Exception("Section %s missing in man page of %s" % (key, checkname))

    parsed["agents"] = parsed["agents"].replace(" ","").split(",")

    if parsed.get("catalog"):
        parsed["catalog"] = parsed["catalog"].split("/")

    return parsed


def load_manpage(checkname):
    filename = all_manuals().get(checkname)
    if not filename:
        return None

    sections = {}
    current_section = []
    current_variable = None
    sections['header'] = current_section
    lineno = 0
    empty_line_count = 0

    try:
        for line in file(filename):
            lineno += 1
            if line.startswith(' ') and line.strip() != "": # continuation line
                empty_line_count = 0
                if current_variable:
                    name, curval = current_section[-1]
                    if curval.strip() == "":
                        current_section[-1] = (name, line.rstrip()[1:])
                    else:
                        current_section[-1] = (name, curval + "\n" + line.rstrip()[1:])
                else:
                    raise Exception
                continue

            line = line.strip()
            if line == "":
                empty_line_count += 1
                if empty_line_count == 1 and current_variable:
                    name, curval = current_section[-1]
                    current_section[-1] = (name, curval + "\n<br>\n")
                continue
            empty_line_count = 0

            if line[0] == '[' and line[-1] == ']':
                section_header = line[1:-1]
                current_section = []
                sections[section_header] = current_section
            else:
                current_variable, restofline = line.split(':', 1)
                current_section.append((current_variable, restofline.lstrip()))

    except Exception, e:
        sys.stderr.write("Syntax error in %s line %d (%s).\n" % (filename, lineno, e))
        sys.exit(1)

    header = {}
    for key, value in sections['header']:
        header[key] = value.strip()
    header["agents"] = [ a.strip() for a in header["agents"].split(",") ]

    if 'catalog' not in header:
        header['catalog'] = [ 'unsorted' ]
    sections['header'] = header

    return sections


def show_check_manual(checkname):

    bg_color = 4
    fg_color = 7
    bold_color = tty_white + tty_bold
    normal_color = tty_normal + tty(fg_color, bg_color)
    title_color_left = tty(0,7,1)
    title_color_right = tty(0,7)
    subheader_color = tty(fg_color, bg_color, 1)
    header_color_left = tty(0,2)
    header_color_right = tty(7,2,1)
    parameters_color = tty(6,4,1)
    examples_color = tty(6,4,1)

    sections = load_manpage(checkname)
    if not sections:
        sys.stdout.write("No manpage for %s. Sorry.\n" % checkname)
        return

    # Output
    height, width = get_tty_size()
    if os.path.exists("/usr/bin/less") and not opt_nowiki:
        output = os.popen("/usr/bin/less -S -R -Q -u -L", "w")
    else:
        output = sys.stdout

    if opt_nowiki:
        print "TI:Check manual page of %s" % checkname
        print "DT:%s" % (time.strftime("%Y-%m-%d"))
        print "SA:checks"

        def markup(line, ignored=None):
            # preserve the inner { and } in double braces and then replace the braces left
            return line.replace('{{', '{&#123;').replace('}}', '&#125;}').replace("{", "<b>").replace("}", "</b>")

        def print_sectionheader(line, title):
            print "H1:" + title

        def print_subheader(line):
            print "H2:" + line

        def print_line(line, attr=None, no_markup = False):
            if no_markup:
                print line
            else:
                print markup(line)

        def print_splitline(attr1, left, attr2, right):
            print "<b style=\"width: 300px;\">%s</b> %s\n" % (left, right)

        def empty_line():
            print

        def print_textbody(text):
            print markup(text)

        def print_splitwrap(attr1, left, attr2, text):
            if '(' in left:
                name, typ = left.split('(', 1)
                name = name.strip()
                typ = typ.strip()[:-2]
            else:
                name = left
                typ = ""
            print "<tr><td class=tt>%s</td><td>%s</td><td>%s</td></tr>" % (name, typ, markup(text))

    else:
        def markup(line, attr):
            # Replaces braces in the line but preserves the inner braces
            return re.sub('(?<!{){', bold_color, re.sub('(?<!})}', tty_normal + attr, line))

        def print_sectionheader(left, right):
            print_splitline(title_color_left, "%-25s" % left, title_color_right, right)

        def print_subheader(line):
            empty_line()
            output.write(subheader_color + " " + tty_underline +
                         line.upper() +
                         normal_color +
                         (" " * (width - 1 - len(line))) +
                         tty_normal + "\n")

        def print_line(line, attr=normal_color, no_markup = False):
            if no_markup:
                text = line
                l = len(line)
            else:
                text = markup(line, attr)
                l = print_len(line)
            output.write(attr + " ")
            output.write(text)
            output.write(" " * (width - 2 - l))
            output.write(" " + tty_normal + "\n")

        def print_splitline(attr1, left, attr2, right):
            output.write(attr1 + " " + left)
            output.write(attr2)
            output.write(markup(right, attr2))
            output.write(" " * (width - 1 - len(left) - print_len(right)))
            output.write(tty_normal + "\n")

        def empty_line():
            print_line("", tty(7,4))

        def print_len(word):
            # In case of double braces remove only one brace for counting the length
            netto = word.replace('{{', 'x').replace('}}', 'x').replace("{", "").replace("}", "")
            netto = re.sub("\033[^m]+m", "", netto)
            return len(netto)

        # only used for debugging
        def remove_ansi(line):
            newline = ""
            ci = 0
            while ci < len(line):
                c = line[ci]
                if c == '\033':
                    while line[ci] != 'm' and ci < len(line):
                        ci += 1
                else:
                    newline += c
                ci += 1

            return newline

        def justify(line, width):
            need_spaces = float(width - print_len(line))
            spaces = float(line.count(' '))
            newline = ""
            x = 0.0
            s = 0.0
            words = line.split()
            newline = words[0]
            for word in words[1:]:
                newline += ' '
                x += 1.0
                while s/x < need_spaces / spaces:
                    newline += ' '
                    s += 1
                newline += word
            return newline

        def fillup(line, width):
            printlen = print_len(line)
            if printlen < width:
                line += " " * (width - printlen)
            return line

        def wrap_text(text, width, attr=tty(7,4)):
            wrapped = []
            line = ""
            col = 0
            for word in text.split():
                if word == '<br>':
                    if line != "":
                        wrapped.append(fillup(line, width))
                        wrapped.append(fillup("", width))
                        line = ""
                        col = 0
                else:
                    netto = print_len(word)
                    if line != "" and netto + col + 1 > width:
                        wrapped.append(justify(line, width))
                        col = 0
                        line = ""
                    if line != "":
                        line += ' '
                        col += 1
                    line += markup(word, attr)
                    col += netto
            if line != "":
                wrapped.append(fillup(line, width))

            # remove trailing empty lines
            while wrapped[-1].strip() == "":
                wrapped = wrapped[:-1]
            return wrapped

        def print_textbody(text, attr=tty(7,4)):
            wrapped = wrap_text(text, width - 2)
            for line in wrapped:
                print_line(line, attr)

        def print_splitwrap(attr1, left, attr2, text):
            wrapped = wrap_text(left + attr2 + text, width - 2)
            output.write(attr1 + " " + wrapped[0] + " " + tty_normal + "\n")
            for line in wrapped[1:]:
                output.write(attr2 + " " + line + " " + tty_normal + "\n")

    try:
        header = sections['header']

        print_sectionheader(checkname, header['title'])
        if opt_nowiki:
            sys.stderr.write("<tr><td class=tt>%s</td><td>[check_%s|%s]</td></tr>\n" % (checkname, checkname, header['title']))
        ags = []
        for agent in header['agents']:
            ags.append({ "vms" : "VMS", "linux":"Linux", "aix": "AIX",
                         "solaris":"Solaris", "windows":"Windows", "snmp":"SNMP",
                         "openvms" : "OpenVMS", "vsphere" : "vSphere" }
                         .get(agent, agent.upper()))
        print_splitline(header_color_left, "Supported Agents:        ", header_color_right, ", ".join(ags))
        distro = header['distribution']
        if distro == 'check_mk':
            distro = "official part of Check_MK"
        print_splitline(header_color_left, "Distribution:            ", header_color_right, distro)
        print_splitline(header_color_left, "License:                 ", header_color_right, header['license'])

        empty_line()
        print_textbody(header['description'])
        if 'item' in header:
            print_subheader("Item")
            print_textbody(header['item'])

        print_subheader("Check parameters")
        if sections.has_key('parameters'):
            if opt_nowiki:
                print "<table><th>Parameter</th><th>Type</th><th>Description</th></tr>"
            first = True
            for name, text in sections['parameters']:
                if not first:
                    empty_line()
                first = False
                print_splitwrap(parameters_color, name + ": ", normal_color, text)
            if opt_nowiki:
                print "</table>"
        else:
            print_line("None.")

        print_subheader("Performance data")
        if header.has_key('perfdata'):
            print_textbody(header['perfdata'])
        else:
            print_textbody("None.")

        print_subheader("Inventory")
        if header.has_key('inventory'):
            print_textbody(header['inventory'])
        else:
            print_textbody("No inventory supported.")

        print_subheader("Configuration variables")
        if sections.has_key('configuration'):
            if opt_nowiki:
                print "<table><th>Variable</th><th>Type</th><th>Description</th></tr>"
            first = True
            for name, text in sections['configuration']:
                if not first:
                    empty_line()
                first = False
                print_splitwrap(tty(2,4,1), name + ": ", tty_normal + tty(7,4), text)
            if opt_nowiki:
                print "</table>"
        else:
            print_line("None.")

        if header.has_key("examples"):
            print_subheader("Examples")
            lines = header['examples'].split('\n')
            if opt_nowiki:
                print "F+:main.mk"
            for line in lines:
                if line.lstrip().startswith('#'):
                    print_line(line)
                elif line != "<br>":
                    print_line(line, examples_color, True) # nomarkup
            if opt_nowiki:
                print "F-:"

        empty_line()
        output.flush()
        output.close()
    except Exception, e:
        sys.stdout.write("Invalid check manpage %s: %s\n" % (checkname, e))


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

class fake_file:
    def __init__(self, content=""):
        self._content = content
        self._pointer = 0

    def size(self):
        return len(self._content)

    def read(self, size):
        size = min(size, len(self._content) - self._pointer)
        new_end = self._pointer + size
        data = self._content[self._pointer:new_end]
        self._pointer = new_end
        return data

    def write(self, data):
        self._content += data

    def content(self):
        return self._content

    def tell(self):
        return self._pointer

    def seek(self, offset, whence=0):
        if whence == 0:
            new_pointer = offset
        elif whence == 1:
            new_pointer = self._pointer + offset
        elif whence == 2:
            new_pointer = self.size() - offset
        else:
            raise IOError("Invalid value for whence")

        if new_pointer < 0:
            raise IOError("Invalid seek")

        self._pointer = new_pointer


def do_backup(tarname):
    import tarfile
    if opt_verbose:
        sys.stderr.write("Creating backup file '%s'...\n" % tarname)
    tar = tarfile.open(tarname, "w:gz")


    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths:
        absdir = os.path.abspath(path)
        if os.path.exists(path):
            if opt_verbose:
                sys.stderr.write("  Adding %s (%s) " %  (descr, absdir))
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
            if opt_verbose:
                sys.stderr.write("(%d bytes)...\n" % info.size)
            tar.addfile(info, fake_file(subdata))

    tar.close()
    if opt_verbose:
        sys.stderr.write("Successfully created backup.\n")


def do_restore(tarname):
    import tarfile, shutil

    if opt_verbose:
        sys.stderr.write("Restoring from '%s'...\n" % tarname)

    if not os.path.exists(tarname):
        raise MKGeneralException("Unable to restore: File does not exist")

    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths:
        absdir = os.path.abspath(path)
        if is_dir:
            basedir = absdir
            filename = "."
            if os.path.exists(absdir):
                if opt_verbose:
                    sys.stderr.write("  Deleting old contents of '%s'\n" % absdir)
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
                            sys.stderr.write("  Warning: cannot delete %s: %s\n" % (p, e))
        else:
            basedir = os.path.dirname(absdir)
            filename = os.path.basename(absdir)
            canonical_path = basedir + "/" + canonical_name
            if os.path.exists(canonical_path):
                if opt_verbose:
                    sys.stderr.write("  Deleting old version of '%s'\n" % canonical_path)
                os.remove(canonical_path)

        if not os.path.exists(basedir):
            if opt_verbose:
                sys.stderr.write("  Creating directory %s\n" %  basedir)
            os.makedirs(basedir)

        if opt_verbose:
            sys.stderr.write("  Extracting %s (%s)\n" % (descr, absdir))
        if is_dir:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null "
                      "| tar xf - -C '%s' '%s' 2>/dev/null" % \
                      (tarname, name + ".tar", basedir, filename))
        else:
            os.system("tar xzf '%s' --force-local --to-stdout '%s' 2>/dev/null > '%s' 2>/dev/null" %
                      (tarname, filename, canonical_path))

        if i_am_root():
            if owned_by_nagios:
                to_user = str(nagios_user)
            else:
                to_user = "root"
            if group_www and www_group != None:
                to_group = ":" + str(www_group)
                if opt_verbose:
                    sys.stderr.write("  Adding group write permissions\n")
                    os.system("chmod -R g+w '%s'" % absdir)
            else:
                to_group = ":root"
            if opt_verbose:
                sys.stderr.write("  Changing ownership to %s%s\n" % (to_user, to_group))
            os.system("chown -R '%s%s' '%s' 2>/dev/null" % (to_user, to_group, absdir))

    if opt_verbose:
        sys.stderr.write("Successfully restored backup.\n")


def do_flush(hosts):
    if not hosts:
        hosts = all_active_hosts()
    for host in hosts:
        sys.stdout.write("%-20s: " % host)
        sys.stdout.flush()
        flushed = False

        # counters
        try:
            os.remove(counters_directory + "/" + host)
            sys.stdout.write(tty_bold + tty_blue + " counters")
            sys.stdout.flush()
            flushed = True
        except:
            pass

        # cache files
        d = 0
        dir = tcp_cache_dir
        if os.path.exists(tcp_cache_dir):
            for f in os.listdir(dir):
                if f == host or f.startswith(host + "."):
                    try:
                        os.remove(dir + "/" + f)
                        d += 1
                        flushed = True
                    except:
                        pass
            if d == 1:
                sys.stdout.write(tty_bold + tty_green + " cache")
            elif d > 1:
                sys.stdout.write(tty_bold + tty_green + " cache(%d)" % d)
            sys.stdout.flush()

        # piggy files from this as source host
        d = remove_piggyback_info_from(host)
        if d:
            sys.stdout.write(tty_bold + tty_magenta  + " piggyback(%d)" % d)


        # logfiles
        dir = logwatch_dir + "/" + host
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
                sys.stdout.write(tty_bold + tty_magenta + " logfiles(%d)" % d)

        # autochecks
        count = remove_autochecks_of(host)
        if count:
            flushed = True
            sys.stdout.write(tty_bold + tty_cyan + " autochecks(%d)" % count)

        # inventory
        path = var_dir + "/inventory/" + host
        if os.path.exists(path):
            os.remove(path)
            sys.stdout.write(tty_bold + tty_yellow + " inventory")

        if not flushed:
            sys.stdout.write("(nothing)")

        sys.stdout.write(tty_normal + "\n")


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
    sys.stdout.write("\n%sWARNING:%s %s\n" % (tty_bold + tty_yellow, tty_normal, text))


def create_core_config():
    global g_configuration_warnings
    g_configuration_warnings = []

    verify_non_duplicate_hosts()
    verify_non_deprecated_checkgroups()

    if monitoring_core == "cmc":
        warnings = do_create_cmc_config(opt_cmc_relfilename)
    else:
        load_module("nagios")
        out = file(nagios_objects_file, "w")
        warnings = create_nagios_config(out)

    num_warnings = len(g_configuration_warnings)
    if num_warnings > 10:
        g_configuration_warnings = g_configuration_warnings[:10] + \
                                  [ "%d further warnings have been omitted" % (num_warnings - 10) ]

    return g_configuration_warnings


# Verify that the user has no deprecated check groups configured.
def verify_non_deprecated_checkgroups():
    groups = checks_by_checkgroup()

    for checkgroup, rules in checkgroup_parameters.items():
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
        if node not in all_active_realhosts():
            configuration_warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
                                                                                      (node, hostname))
            nodes.remove(node)
    return nodes


def get_basic_host_macros_from_attributes(hostname, attrs):
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


def get_host_attributes(hostname):
    attrs = extra_host_attributes(hostname)

    if "alias" not in attrs:
        attrs["alias"] = alias_of(hostname, hostname)

    # Now lookup configured IP addresses
    if is_ipv4_host(hostname):
        attrs["_ADDRESS_4"] = ip_address_of(hostname, 4)
    else:
        attrs["_ADDRESS_4"] = ""

    if is_ipv6_host(hostname):
        attrs["_ADDRESS_6"] = ip_address_of(hostname, 6)
    else:
        attrs["_ADDRESS_6"] = ""

    ipv6_primary = is_ipv6_primary(hostname)
    if ipv6_primary:
        attrs["address"]        = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"]        = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    return attrs


def extra_host_attributes(hostname):
    attrs = {}
    for key, conflist in extra_host_conf.items():
        values = host_extra_conf(hostname, conflist)
        if values:
            if key[0] == "_":
                key = key.upper()
            attrs[key] = values[0]
    return attrs


def get_cluster_attributes(hostname, nodes):
    attrs = {}
    node_ips_4 = []
    if is_ipv4_host(hostname):
        for h in nodes:
            addr = ip_address_of(h, 4)
            if addr != None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(fallback_ip_for(hostname, 4))

    node_ips_6 = []
    if is_ipv6_host(hostname):
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


def ip_address_of(hostname, family=None):
    try:
        return lookup_ip_address(hostname, family)
    except Exception, e:
        if is_cluster(hostname):
            return ""
        else:
            g_failed_ip_lookups.append(hostname)
            addr = fallback_ip_for(hostname, family)
            if not ignore_ip_lookup_failures:
                configuration_warning("Cannot lookup IP address of '%s' (%s). Using "
                                      "address %s instead." % (hostname, e, addr))
            return addr


def fallback_ip_for(hostname, family=None):
    if family == None:
        family = is_ipv6_primary(hostname) and 6 or 4

    if family == 4:
        return "0.0.0.0"
    else:
        return "::"


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
    for hn in all_active_hosts():
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
    for h in all_active_hosts():
        if hosttags_match_taglist(tags_of_host(h), tags):
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

    walk_path = "%s/%s" % (snmpwalks_dir, walk_filename)
    if not os.path.exists(walk_path):
        raise MKGeneralException("Walk does not exist")

    def translate(lines):
        result_lines = []
        try:
            oids_for_command = []
            for line in lines:
                oids_for_command.append(line.split(" ")[0])

            extra_mib_path = ""
            if local_mibs_dir:
                extra_mib_path = " -M+%s" % local_mibs_dir
            command = "snmptranslate -m ALL%s %s 2>/dev/null" % (extra_mib_path, " ".join(oids_for_command))
            process = os.popen(command, "r")
            output  = process.read()
            result  = output.split("\n")[0::2]
            for idx, line in enumerate(result):
                result_lines.append((line.strip(), lines[idx].strip()))

        except Exception, e:
            print e

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

    if not os.path.exists(snmpwalks_dir):
        os.makedirs(snmpwalks_dir)

    for host in hostnames:
        try:
            do_snmpwalk_on(host, snmpwalks_dir + "/" + host)
        except Exception, e:
            sys.stderr.write("Error walking %s: %s\n" % (host, e))
            if opt_debug:
                raise
        cleanup_globals()


def do_snmpwalk_on(hostname, filename):
    verbose("%s:\n" % hostname)
    ip = lookup_ipv4_address(hostname)

    out = file(filename, "w")
    oids_to_walk = opt_oids
    if not opt_oids:
        oids_to_walk = [
            ".1.3.6.1.2.1", # SNMPv2-SMI::mib-2
            ".1.3.6.1.4.1"  # SNMPv2-SMI::enterprises
        ] + opt_extra_oids

    for oid in oids_to_walk:
        try:
            verbose("Walk on \"%s\"..." % oid)

            if is_inline_snmp_host(hostname):
                rows = inline_snmpwalk_on_suboid(hostname, None, oid)
                rows = inline_convert_rows_for_stored_walk(rows)
            else:
                rows = snmpwalk_on_suboid(hostname, ip, oid, hex_plain = True)

            for oid, value in rows:
                out.write("%s %s\n" % (oid, value))
            verbose("%d variables.\n" % len(rows))
        except:
            if opt_debug:
                raise

    out.close()
    verbose("Successfully Wrote %s%s%s.\n" % (tty_bold, filename, tty_normal))


def do_snmpget(oid, hostnames):
    if len(hostnames) == 0:
        for host in all_active_realhosts():
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
        ( modules_dir,                 dir, inst, "Main components of check_mk"),
        ( checks_dir,                  dir, inst, "Checks"),
        ( notifications_dir,           dir, inst, "Notification scripts"),
        ( inventory_dir,               dir, inst, "Inventory plugins"),
        ( agents_dir,                  dir, inst, "Agents for operating systems"),
        ( doc_dir,                     dir, inst, "Documentation files"),
        ( web_dir,                     dir, inst, "Check_MK's web pages"),
        ( check_manpages_dir,          dir, inst, "Check manpages (for check_mk -M)"),
        ( lib_dir,                     dir, inst, "Binary plugins (architecture specific)"),
        ( pnp_templates_dir,           dir, inst, "Templates for PNP4Nagios"),
    ]
    if monitoring_core == "nagios":
        paths += [
            ( nagios_startscript,          fil, inst, "Startscript for Nagios daemon"),
            ( nagios_binary,               fil, inst, "Path to Nagios executable"),
        ]

    paths += [
        ( default_config_dir,          dir, conf, "Directory that contains main.mk"),
        ( check_mk_configdir,          dir, conf, "Directory containing further *.mk files"),
        ( nagios_config_file,          fil, conf, "Main configuration file of Nagios"),
        ( nagios_conf_dir,             dir, conf, "Directory where Nagios reads all *.cfg files"),
        ( apache_config_dir,           dir, conf, "Directory where Apache reads all config files"),
        ( htpasswd_file,               fil, conf, "Users/Passwords for HTTP basic authentication"),

        ( var_dir,                     dir, data, "Base working directory for variable data"),
        ( autochecksdir,               dir, data, "Checks found by inventory"),
        ( precompiled_hostchecks_dir,  dir, data, "Precompiled host checks"),
        ( snmpwalks_dir,               dir, data, "Stored snmpwalks (output of --snmpwalk)"),
        ( counters_directory,          dir, data, "Current state of performance counters"),
        ( tcp_cache_dir,               dir, data, "Cached output from agents"),
        ( logwatch_dir,                dir, data, "Unacknowledged logfiles of logwatch extension"),
        ( nagios_objects_file,         fil, data, "File into which Nagios configuration is written"),
        ( nagios_status_file,          fil, data, "Path to Nagios status.dat"),

        ( nagios_command_pipe_path,    fil, pipe, "Nagios' command pipe"),
        ( check_result_path,           fil, pipe, "Nagios' check results directory"),
        ( livestatus_unix_socket,      fil, pipe, "Socket of Check_MK's livestatus module"),
        ]

    if omd_root:
        paths += [
         ( local_checks_dir,           dir, local, "Locally installed checks"),
         ( local_notifications_dir,    dir, local, "Locally installed notification scripts"),
         ( local_inventory_dir,        dir, local, "Locally installed inventory plugins"),
         ( local_check_manpages_dir,   dir, local, "Locally installed check man pages"),
         ( local_agents_dir,           dir, local, "Locally installed agents and plugins"),
         ( local_web_dir,              dir, local, "Locally installed Multisite addons"),
         ( local_pnp_templates_dir,    dir, local, "Locally installed PNP templates"),
         ( local_doc_dir,              dir, local, "Locally installed documentation"),
         ( local_locale_dir,           dir, local, "Locally installed localizations"),
        ]

    def show_paths(title, t):
        if t != inst:
            print
        print(tty_bold + title + tty_normal)
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == dir:
                    path += "/"
                print("  %-47s: %s%s%s" % (descr, tty_bold + tty_blue, path, tty_normal))

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
        hostlist = all_active_hosts()
    hostlist.sort()
    for hostname in hostlist:
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
    print
    if is_cluster(hostname):
        color = tty_bgmagenta
        add_txt = " (cluster of " + (", ".join(nodes_of(hostname))) + ")"
    else:
        color = tty_bgblue
        add_txt = ""
    print "%s%s%s%-78s %s" % (color, tty_bold, tty_white, hostname + add_txt, tty_normal)

    ipaddress = ip_address_for_dump_host(hostname)

    addresses = ""
    if not is_ipv4v6_host(hostname):
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

    print tty_yellow + "Addresses:              " + tty_normal + addresses

    tags = tags_of_host(hostname)
    print tty_yellow + "Tags:                   " + tty_normal + ", ".join(tags)
    if is_cluster(hostname):
        parents_list = nodes_of(hostname)
    else:
        parents_list = parents_of(hostname)
    if len(parents_list) > 0:
        print tty_yellow + "Parents:                " + tty_normal + ", ".join(parents_list)
    print tty_yellow + "Host groups:            " + tty_normal + make_utf8(", ".join(hostgroups_of(hostname)))
    print tty_yellow + "Contact groups:         " + tty_normal + make_utf8(", ".join(host_contactgroups_of([hostname])))

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

    print tty_yellow + "Type of agent:          " + tty_normal + '\n                        '.join(agenttypes)
    is_aggregated = host_is_aggregated(hostname)
    if is_aggregated:
        print tty_yellow + "Is aggregated:          " + tty_normal + "yes"
        shn = summary_hostname(hostname)
        print tty_yellow + "Summary host:           " + tty_normal + shn
        print tty_yellow + "Summary host groups:    " + tty_normal + ", ".join(summary_hostgroups_of(hostname))
        print tty_yellow + "Summary contact groups: " + tty_normal + ", ".join(host_contactgroups_of([shn]))
        notperiod = (host_extra_conf(hostname, summary_host_notification_periods) + [""])[0]
        print tty_yellow + "Summary notification:   " + tty_normal + notperiod
    else:
        print tty_yellow + "Is aggregated:          " + tty_normal + "no"


    format_string = " %-15s %s%-10s %s%-17s %s%-14s%s %s%-16s%s"
    print tty_yellow + "Services:" + tty_normal
    check_items = get_sorted_check_table(hostname)

    headers = ["checktype", "item",    "params", "description", "groups", "summarized to", "groups"]
    colors =  [ tty_normal,  tty_blue, tty_normal, tty_green,     tty_normal, tty_red, tty_white ]
    if service_dependencies != []:
        headers.append("depends on")
        colors.append(tty_magenta)

    def if_aggr(a):
        if is_aggregated:
            return a
        else:
            return ""

    print_table(headers, colors, [ [
        checktype,
        make_utf8(item),
        params,
        make_utf8(description),
        make_utf8(",".join(service_extra_conf(hostname, description, service_groups))),
        if_aggr(aggregated_service_name(hostname, description)),
        if_aggr(",".join(service_extra_conf(hostname, aggregated_service_name(hostname, description), summary_service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")

def print_table(headers, colors, rows, indent = ""):
    lengths = [ len(h) for h in headers ]
    for row in rows:
        lengths = [ max(len(str(make_utf8(c))), l) for c, l in zip(row, lengths) ]
    sumlen = sum(lengths) + len(headers)
    format = indent
    sep = ""
    for l,c in zip(lengths, colors):
        format += c + sep + "%-" + str(l) + "s" + tty_normal
        sep = " "

    first = True
    for row in [ headers ] + rows:
        print format % tuple(row[:len(headers)])
        if first:
            first = False
            print format % tuple([ "-" * l for l in lengths ])

def print_version():
    print """This is check_mk version %s
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
""" % check_mk_version

def usage():
    print """WAYS TO CALL:
 cmk [-n] [-v] [-p] HOST [IPADDRESS]  check all services on HOST
 cmk -I [HOST ..]                     inventory - find new services
 cmk -II ...                          renew inventory, drop old services
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
  --interactive  Some errors are only reported in interactive mode, i.e. if stdout
                 is a TTY. This option forces interactive mode even if the output
                 is directed into a pipe or file.
  --procs N      start up to N processes in parallel during --scan-parents
  --checks A,..  restrict checks/inventory to specified checks (tcp/snmp/check type)
  --keepalive    used by Check_MK Mirco Core: run check and --notify
                 in continous mode. Read data from stdin and from cmd line.
  --cmc-file=X   relative filename for CMC config file (used by -B/-U)
  --extraoid A   Do --snmpwalk also on this OID, in addition to mib-2 and enterprises.
                 You can specify this option multiple times.
  --oid A        Do --snmpwalk on this OID instead of mib-2 and enterprises.
                 You can specify this option multiple times.
  --hw-changes=S --inventory-as-check: Use monitoring state S for HW changes
  --sw-changes=S --inventory-as-check: Use monitoring state S for SW changes
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

  -U redirects both the output of -S and -H to the file %s
  and also calls check_mk -C.

  -D, --dump dumps out the complete configuration and information
  about one, several or all hosts. It shows all services, hostgroups,
  contacts and other information about that host.

  -d does not work on clusters (such defined in main.mk) but only on
  real hosts.

  --check-discovery make check_mk behave as monitoring plugins that
  checks if an inventory would find new or vanished services for the host.
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
  result in the directory %s. Use the option --oid one or several
  times in order to specify alternative OIDs to walk. You need to
  specify numeric OIDs. If you want to keep the two standard OIDS
  .1.3.6.1.2.1  and .1.3.6.1.4.1 then use --extraoid for just adding
  additional OIDs to walk.

  --snmptranslate does not contact the host again, but reuses the hosts
  walk from the directory %s.%s

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


""" % (check_mk_configfile,
       precompiled_hostchecks_dir,
       snmpwalks_dir,
       snmpwalks_dir,
       local_mibs_dir and ("\n  You can add further MIBs to %s" % local_mibs_dir) or "",
       )


def do_create_config(with_agents=True):
    sys.stdout.write("Generating configuration for core (type %s)..." % monitoring_core)
    sys.stdout.flush()
    create_core_config()
    sys.stdout.write(tty_ok + "\n")

    if bake_agents_on_restart and with_agents and 'do_bake_agents' in globals():
        sys.stdout.write("Baking agents...")
        sys.stdout.flush()
        try:
            do_bake_agents()
            sys.stdout.write(tty_ok + "\n")
        except Exception, e:
            if opt_debug:
               raise
            sys.stdout.write("Error: %s\n" % e)


def do_precompile_hostchecks():
    sys.stdout.write("Precompiling host checks...")
    sys.stdout.flush()
    precompile_hostchecks()
    sys.stdout.write(tty_ok + "\n")


def do_pack_config():
    sys.stdout.write("Packing config...")
    sys.stdout.flush()
    pack_config()
    pack_autochecks()
    sys.stdout.write(tty_ok + "\n")


def do_update(with_precompile):
    try:
        do_create_config(with_agents=with_precompile)
        if with_precompile:
            if monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()

    except Exception, e:
        sys.stderr.write("Configuration Error: %s\n" % e)
        if opt_debug:
            raise
        sys.exit(1)

def do_check_nagiosconfig():
    if monitoring_core == 'nagios':
        command = nagios_binary + " -vp "  + nagios_config_file + " 2>&1"
        sys.stdout.write("Validating Nagios configuration...")
        if opt_verbose:
            sys.stderr.write("Running '%s'" % command)
        sys.stderr.flush()

        process = os.popen(command, "r")
        output = process.read()
        exit_status = process.close()
        if not exit_status:
            sys.stdout.write(tty_ok + "\n")
            return True
        else:
            sys.stdout.write("ERROR:\n")
            sys.stderr.write(output)
            return False
    else:
        return True


# Action can be restart, reload, start or stop
def do_core_action(action, quiet=False):
    if not quiet:
        sys.stdout.write("%sing monitoring core..." % action.title())
        sys.stdout.flush()
    if monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = nagios_startscript + " %s 2>&1" % action
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
            sys.stdout.write(tty_ok + "\n")

def core_is_running():
    if monitoring_core == "nagios":
        command = nagios_startscript + " status >/dev/null 2>&1"
    else:
        command = "omd status cmc >/dev/null 2>&1"
    code = os.system(command)
    return not code


def do_reload():
    do_restart(True)

def do_restart(only_reload = False):
    try:
        backup_path = None

        if another_activation_is_in_progress():
            sys.stderr.write("Other restart currently in progress. Aborting.\n")
            sys.exit(1)

        # Save current configuration
        if os.path.exists(nagios_objects_file):
            backup_path = nagios_objects_file + ".save"
            if opt_verbose:
                sys.stderr.write("Renaming %s to %s\n" % (nagios_objects_file, backup_path))
            os.rename(nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
            do_create_config(with_agents=True)
        except Exception, e:
            sys.stderr.write("Error creating configuration: %s\n" % e)
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            if opt_debug:
                raise
            sys.exit(1)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            if monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()
            do_core_action(only_reload and "reload" or "restart")
        else:
            sys.stderr.write("Configuration for monitoring core is invalid. Rolling back.\n")
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            else:
                os.remove(nagios_objects_file)
            sys.exit(1)

    except Exception, e:
        try:
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
        except:
            pass
        if opt_debug:
            raise
        sys.stderr.write("An error occurred: %s\n" % e)
        sys.exit(1)

restart_lock_fd = None
def another_activation_is_in_progress():
    global restart_lock_fd
    # In some bizarr cases (as cmk -RR) we need to avoid duplicate locking!
    if restart_locking and restart_lock_fd == None:
        lock_file = default_config_dir + "/main.mk"
        import fcntl
        restart_lock_fd = os.open(lock_file, os.O_RDONLY)
        # Make sure that open file is not inherited to monitoring core!
        fcntl.fcntl(restart_lock_fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        try:
            if opt_debug:
                sys.stderr.write("Waiting for exclusive lock on %s.\n" %
                    lock_file)
            fcntl.flock(restart_lock_fd, fcntl.LOCK_EX |
                ( restart_locking == "abort" and fcntl.LOCK_NB or 0))
        except:
            return True
    return False


def do_donation():
    donate = []
    cache_files = os.listdir(tcp_cache_dir)
    for host in all_active_realhosts():
        if in_binary_hostlist(host, donation_hosts):
            for f in cache_files:
                if f == host or f.startswith("%s." % host):
                    donate.append(f)
    if not donate:
        sys.stderr.write("No hosts specified. You need to set donation_hosts in main.mk.\n")
        sys.exit(1)

    if opt_verbose:
        print "Donating files %s" % " ".join(cache_files)
    import base64
    indata = base64.b64encode(os.popen("tar czf - -C %s %s" % (tcp_cache_dir, " ".join(donate))).read())
    output = os.popen(donation_command, "w")
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
    global max_num_processes
    if len(hosts) == 0:
        hosts = filter(lambda h: in_binary_hostlist(h, scanparent_hosts), all_active_realhosts())

    found = []
    parent_hosts = []
    parent_ips   = {}
    parent_rules = []
    gateway_hosts = set([])

    if max_num_processes < 1:
        max_num_processes = 1

    outfilename = check_mk_configdir + "/parents.mk"

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

    sys.stdout.write("Scanning for parents (%d processes)..." % max_num_processes)
    sys.stdout.flush()
    while len(hosts) > 0:
        chunk = []
        while len(chunk) < max_num_processes and len(hosts) > 0:
            host = hosts[0]
            del hosts[0]
            # skip hosts that already have a parent
            if len(parents_of(host)) > 0:
                if opt_verbose:
                    sys.stdout.write("(manual parent) ")
                    sys.stdout.flush()
                continue
            chunk.append(host)

        gws = scan_parents_of(chunk)

        for host, (gw, state, ping_fails, message) in zip(chunk, gws):
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
                        if monitoring_host:
                            parent_rules.append( (monitoring_host, [gateway]) ) # make Nagios a parent of gw
                parent_rules.append( (gateway, [host]) )
            elif host != monitoring_host and monitoring_host:
                # make monitoring host the parent of all hosts without real parent
                parent_rules.append( (monitoring_host, [host]) )

    import pprint
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
      (probes, quote_shell_string(ip))) >> 8

def scan_parents_of(hosts, silent=False, settings={}):
    if monitoring_host:
        nagios_ip = lookup_ipv4_address(monitoring_host)
    else:
        nagios_ip = None

    os.putenv("LANG", "")
    os.putenv("LC_ALL", "")

    # Start processes in parallel
    procs = []
    for host in hosts:
        if opt_verbose:
            sys.stdout.write("%s " % host)
            sys.stdout.flush()
        try:
            ip = lookup_ipv4_address(host)
            command = "traceroute -w %d -q %d -m %d -n %s 2>&1" % (
                settings.get("timeout", 8),
                settings.get("probes", 2),
                settings.get("max_ttl", 10),
                quote_shell_string(ip))
            if opt_debug:
                sys.stderr.write("Running '%s'\n" % command)
            procs.append( (host, ip, os.popen(command) ) )
        except:
            procs.append( (host, None, os.popen(
                "echo 'ERROR: cannot resolve host name'")))

    # Output marks with status of each single scan
    def dot(color, dot='o'):
        if not silent:
            sys.stdout.write(tty_bold + color + dot + tty_normal)
            sys.stdout.flush()

    # Now all run and we begin to read the answers. For each host
    # we add a triple to gateways: the gateway, a scan state  and a diagnostic output
    gateways = []
    for host, ip, proc in procs:
        lines = [l.strip() for l in proc.readlines()]
        exitstatus = proc.close()
        if exitstatus:
            dot(tty_red, '*')
            gateways.append((None, "failed", 0, "Traceroute failed with exit code %d" % (exitstatus & 255)))
            continue

        if len(lines) == 1 and lines[0].startswith("ERROR:"):
            message = lines[0][6:].strip()
            if opt_verbose:
                sys.stderr.write("%s: %s\n" % (host, message))
            dot(tty_red, "D")
            gateways.append((None, "dnserror", 0, message))
            continue

        elif len(lines) == 0:
            if opt_debug:
                raise MKGeneralException("Cannot execute %s. Is traceroute installed? Are you root?" % command)
            else:
                dot(tty_red, '!')
            continue

        elif len(lines) < 2:
            if not silent:
                sys.stderr.write("%s: %s\n" % (host, ' '.join(lines)))
            gateways.append((None, "garbled", 0, "The output of traceroute seem truncated:\n%s" %
                    ("".join(lines))))
            dot(tty_blue)
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
            dot(tty_red)
            continue

        # Only one entry -> host is directly reachable and gets nagios as parent -
        # if nagios is not the parent itself. Problem here: How can we determine
        # if the host in question is the monitoring host? The user must configure
        # this in monitoring_host.
        elif len(routes) == 1:
            if ip == nagios_ip:
                gateways.append( (None, "root", 0, "") ) # We are the root-monitoring host
                dot(tty_white, 'N')
            elif monitoring_host:
                gateways.append( ((monitoring_host, nagios_ip, None), "direct", 0, "") )
                dot(tty_cyan, 'L')
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
                    if opt_verbose:
                        sys.stderr.write("(not using %s, not reachable)\n" % r)
                    skipped_gateways += 1
                    continue
            route = r
            break
        if not route:
            error = "No usable routing information"
            if not silent:
                sys.stderr.write("%s: %s\n" % (host, error))
            gateways.append((None, "notfound", 0, error))
            dot(tty_blue)
            continue

        # TTLs already have been filtered out)
        gateway_ip = route
        gateway = ip_to_hostname(route)
        if opt_verbose:
            if gateway:
                sys.stdout.write("%s(%s) " % (gateway, gateway_ip))
            else:
                sys.stdout.write("%s " % gateway_ip)

        # Try to find DNS name of host via reverse DNS lookup
        dns_name = ip_to_dnsname(gateway_ip)
        gateways.append( ((gateway, gateway_ip, dns_name), "gateway", skipped_gateways, "") )
        dot(tty_green, 'G')
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
        for host in all_active_realhosts():
            try:
                ip_to_hostname_cache[lookup_ipv4_address(host)] = host
            except:
                pass
    return ip_to_hostname_cache.get(ip)

def ip_to_dnsname(ip):
    try:
        dnsname, aliaslist, addresslist = socket.gethostbyaddr(ip)
        return dnsname
    except:
        return None

def config_timestamp():
    mtime = 0
    for dirpath, dirnames, filenames in os.walk(check_mk_configdir):
        for f in filenames:
            mtime = max(mtime, os.stat(dirpath + "/" + f).st_mtime)
    mtime = max(mtime, os.stat(default_config_dir + "/main.mk").st_mtime)
    try:
        mtime = max(mtime, os.stat(default_config_dir + "/final.mk").st_mtime)
    except:
        pass
    try:
        mtime = max(mtime, os.stat(default_config_dir + "/local.mk").st_mtime)
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
    global g_hostname
    g_hostname = "unknown"
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



#.
#   .--Read Config---------------------------------------------------------.
#   |        ____                _    ____             __ _                |
#   |       |  _ \ ___  __ _  __| |  / ___|___  _ __  / _(_) __ _          |
#   |       | |_) / _ \/ _` |/ _` | | |   / _ \| '_ \| |_| |/ _` |         |
#   |       |  _ <  __/ (_| | (_| | | |__| (_) | | | |  _| | (_| |         |
#   |       |_| \_\___|\__,_|\__,_|  \____\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+
#   | Code for reading the configuration files.                            |
#   '----------------------------------------------------------------------'

# These variables shal be ignored when performing checks which global
# variables have been changed during runtime of e.g. the Check_MK
# keepalive mode
ignore_changed_global_variables = [
    'all_hosts_untagged',
    'all_clusters_untagged',
]

vars_before_config = set([])

# Now - at last - we can read in the user's configuration files
def all_nonfunction_vars():
    return set([ name for name,value in globals().items()
                if name[0] != '_' and type(value) != type(lambda:0) ])

def marks_hosts_with_path(old, all, filename):
    if not filename.startswith(check_mk_configdir):
        return
    path = filename[len(check_mk_configdir):]
    old = set([ o.split("|", 1)[0] for o in old ])
    all = set([ a.split("|", 1)[0] for a in all ])
    for host in all:
        if host not in old:
            host_paths[host] = path


# Helper functions that determines the sort order of the
# configuration files. The following two rules are implemented:
# 1. *.mk files in the same directory will be read
#    according to their lexical order.
# 2. subdirectories in the same directory will be
#    scanned according to their lexical order.
# 3. subdirectories of a directory will always be read *after*
#    the *.mk files in that directory.
def cmp_config_paths(a, b):
    pa = a.split('/')
    pb = b.split('/')
    return cmp(pa[:-1], pb[:-1]) or \
           cmp(len(pa), len(pb)) or \
           cmp(pa, pb)


# Abort after an error, but only in interactive mode.
def interactive_abort(error):
    if sys.stdout.isatty() or opt_interactive:
        sys.stderr.write(error + "\n")
        sys.exit(1)


def read_config_files(with_conf_d=True, validate_hosts=True):
    global vars_before_config, final_mk, local_mk, checks

    # Initialize dictionary-type default levels variables
    for check in check_info.values():
        def_var = check.get("default_levels_variable")
        if def_var:
            globals()[def_var] = {}

    # Create list of all files to be included
    if with_conf_d:
        list_of_files = reduce(lambda a,b: a+b,
           [ [ "%s/%s" % (d, f) for f in fs if f.endswith(".mk")]
             for d, sb, fs in os.walk(check_mk_configdir) ], [])
        # list_of_files.sort()
        list_of_files.sort(cmp = cmp_config_paths)
        list_of_files = [ check_mk_configfile ] + list_of_files
    else:
        list_of_files = [ check_mk_configfile ]

    final_mk = check_mk_basedir + "/final.mk"
    if os.path.exists(final_mk):
        list_of_files.append(final_mk)
    local_mk = check_mk_basedir + "/local.mk"
    if os.path.exists(local_mk):
        list_of_files.append(local_mk)

    global FILE_PATH, FOLDER_PATH
    FILE_PATH = None
    FOLDER_PATH = None

    vars_before_config = all_nonfunction_vars()
    for _f in list_of_files:
        # Hack: during parent scan mode we must not read in old version of parents.mk!
        if '--scan-parents' in sys.argv and _f.endswith("/parents.mk"):
            continue
        try:
            _old_all_hosts = all_hosts[:]
            _old_clusters = clusters.keys()
            # Make the config path available as a global variable to
            # be used within the configuration file
            if _f.startswith( check_mk_configdir + "/"):
                FILE_PATH = _f[len(check_mk_configdir) + 1:]
                FOLDER_PATH = os.path.dirname(FILE_PATH)
            else:
                FILE_PATH = None
                FOLDER_PATH = None

            execfile(_f, globals(), globals())
            marks_hosts_with_path(_old_all_hosts, all_hosts, _f)
            marks_hosts_with_path(_old_clusters, clusters.keys(), _f)
        except Exception, e:
            if opt_debug:
                raise
            else:
                interactive_abort("Cannot read in configuration file %s: %s" % (_f, e))

    collect_hosttags()

    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])

    if validate_hosts:
        duplicates = duplicate_hosts()
        if duplicates:
            sys.stderr.write("Error in configuration: duplicate hosts: %s\n" % ", ".join(duplicates))
            sys.exit(3)

    # Add WATO-configured explicit checks to (possibly empty) checks
    # statically defined in checks.
    static = []
    for entries in static_checks.values():
        for entry in entries:
            entry, rule_options = get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            # Parameters are optional
            if len(entry[0]) == 2:
                checktype, item = entry[0]
                params = None
            else:
                checktype, item, params = entry[0]
            if len(entry) == 3:
                taglist, hostlist = entry[1:3]
            else:
                hostlist = entry[1]
                taglist = []
            # Make sure, that for dictionary based checks
            # at least those keys defined in the factory
            # settings are present in the parameters
            if type(params) == dict:
                def_levels_varname = check_info[checktype].get("default_levels_variable")
                if def_levels_varname:
                    for key, value in factory_settings.get(def_levels_varname, {}).items():
                        if key not in params:
                            params[key] = value

            static.append((taglist, hostlist, checktype, item, params))

    # Note: We need to reverse the order of the static_checks. This is because
    # users assume that earlier rules have precedence over later ones. For static
    # checks that is important if there are two rules for a host with the same
    # combination of check type and item. When the variable 'checks' is evaluated,
    # *later* rules have precedence. This is not consistent with the rest, but a
    # result of this "historic implementation".
    static.reverse()

    # Now prepend to checks. That makes that checks variable have precedence
    # over WATO.
    checks = static + checks

    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'parts',
                             'hosttags' ,'seen_hostnames',
                             'taggedhost' ,'hostname'] + ignore_changed_global_variables)
    errors = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            sys.stderr.write("Invalid configuration variable '%s'\n" % name)
            errors += 1

    # Special handling for certain deprecated variables
    if type(snmp_communities) == dict:
        sys.stderr.write("ERROR: snmp_communities cannot be a dict any more.\n")
        errors += 1

    if errors > 0:
        sys.stderr.write("--> Found %d invalid variables\n" % errors)
        sys.stderr.write("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)

    # Prepare information for --backup and --restore
    global backup_paths
    backup_paths = [
        # tarname               path                 canonical name   description                is_dir owned_by_nagios www_group
        ('check_mk_configfile', check_mk_configfile, "main.mk",       "Main configuration file",           False, False, False ),
        ('final_mk',            final_mk,            "final.mk",      "Final configuration file final.mk", False, False, False ),
        ('check_mk_configdir',  check_mk_configdir,  "",              "Configuration sub files",           True,  False, False ),
        ('autochecksdir',       autochecksdir,       "",              "Automatically inventorized checks", True,  False, False ),
        ('counters_directory',  counters_directory,  "",              "Performance counters",              True,  True,  False ),
        ('tcp_cache_dir',       tcp_cache_dir,       "",              "Agent cache",                       True,  True,  False ),
        ('logwatch_dir',        logwatch_dir,        "",              "Logwatch",                          True,  True,  True  ),
        ]


# Compute parameters for a check honoring factory settings,
# default settings of user in main.mk, check_parameters[] and
# the values code in autochecks (given as parameter params)
def compute_check_parameters(host, checktype, item, params):
    if checktype not in check_info: # handle vanished checktype
        return None

    # Handle dictionary based checks
    def_levels_varname = check_info[checktype].get("default_levels_variable")
    if def_levels_varname:
        vars_before_config.add(def_levels_varname)

    # Handle case where parameter is None but the type of the
    # default value is a dictionary. This is for example the
    # case if a check type has gotten parameters in a new version
    # but inventory of the old version left None as a parameter.
    # Also from now on we support that the inventory simply puts
    # None as a parameter. We convert that to an empty dictionary
    # that will be updated with the factory settings and default
    # levels, if possible.
    if params == None and def_levels_varname:
        fs = factory_settings.get(def_levels_varname)
        if type(fs) == dict:
            params = {}

    # Honor factory settings for dict-type checks. Merge
    # dict type checks with multiple matching rules
    if type(params) == dict:

        # Start with factory settings
        if def_levels_varname:
            new_params = factory_settings.get(def_levels_varname, {}).copy()
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
    entries += service_extra_conf(host, descr, check_parameters)

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
    checkgroup = check_info[checktype]["group"]
    if not checkgroup:
        return []
    rules = checkgroup_parameters.get(checkgroup)
    if rules == None:
        return []

    try:
        # checks without an item
        if item == None and checkgroup not in service_rule_groups:
            return host_extra_conf(host, rules)
        else: # checks with an item need service-specific rules
            return service_extra_conf(host, item, rules)
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
load_checks()

opt_nowiki     = False
opt_split_rrds = False
opt_delete_rrds = False

# Do option parsing and execute main function -
short_options = 'ASHVLCURODMmd:Ic:nhvpXPNBilf'
long_options = [ "help", "version", "verbose", "compile", "debug", "interactive",
                 "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
                 "flush", "package", "localize", "donate", "snmpwalk", "oid=", "extraoid=",
                 "snmptranslate", "bake-agents", "force", "show-snmp-stats",
                 "usewalk", "scan-parents", "procs=", "automation=", "handle-alerts", "notify",
                 "snmpget=", "profile", "keepalive", "keepalive-fd=", "create-rrd",
                 "convert-rrds", "compress-history", "split-rrds", "delete-rrds",
                 "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                 "man", "nowiki", "config-check", "backup=", "restore=",
                 "check-inventory=", "check-discovery=", "discover-marked-hosts", "paths",
                 "checks=", "inventory", "inventory-as-check=", "hw-changes=", "sw-changes=", "inv-fail-status=",
                 "cmc-file=", "browse-man", "list-man", "update-dns-cache", "cap", "real-time-checks" ]

non_config_options = ['-L', '--list-checks', '-P', '--package', '-M',
                      '--handle-alerts', '--notify', '--real-time-checks',
                      '--man', '-V', '--version' ,'-h', '--help', '--automation',
                      '--create-rrd', '--convert-rrds', '--compress-history', '--keepalive', '--cap' ]

try:
    opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
except getopt.GetoptError, err:
    print str(err)
    sys.exit(1)

# Read the configuration files (main.mk, autochecks, etc.), but not for
# certain operation modes that does not need them and should not be harmed
# by a broken configuration
if len(set.intersection(set(non_config_options), [o[0] for o in opts])) == 0:
    read_config_files()

done = False
seen_I = 0
check_types = None
exit_status = 0
opt_verbose = 0 # start again from 0, was already faked at the beginning
opt_inv_hw_changes = 0
opt_inv_sw_changes = 0
opt_inv_fail_status = 1 # State in case of an error (default: WARN)

# Scan modifying options first (makes use independent of option order)
for o,a in opts:
    if o in [ '-v', '--verbose' ]:
        opt_verbose += 1
    elif o in [ '-f', '--force' ]:
        opt_force = True
    elif o == '-c':
        if check_mk_configfile != a:
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
        max_num_processes = int(a)
    elif o == '--nowiki':
        opt_nowiki = True
    elif o == '--debug':
        opt_debug = True
    elif o == '--interactive':
        opt_interactive = True
    elif o == '-I':
        seen_I += 1
    elif o == "--checks":
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
    elif o == "--inv-fail-status":
        opt_inv_fail_status = int(a)

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
            sys.stderr.write(tty_bold + tty_red + "ERROR" + tty_normal + "\n")
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
            load_module("packaging")
            do_packaging(args)
            done = True
        elif o in ['--localize']:
            load_module("localize")
            do_localize(args)
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
            if len(args) > 0:
                show_check_manual(args[0])
            else:
                list_all_manuals()
            done = True
        elif o in [ '--list-man' ]:
            read_manpage_catalog()
            print pprint.pformat(g_manpage_catalog)
            done = True
        elif o in [ '-m', '--browse-man' ]:
            manpage_browser()
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
                hostnames = parse_hostname_list(args, with_clusters = False)
            else:
                hostnames = None
            do_inv(hostnames)
            done = True
        elif o == '--inventory-as-check':
            load_module("inventory")
            do_inv_check(a)
            done = True

        elif o == '--handle-alerts':
            read_config_files(with_conf_d=True, validate_hosts=False)
            sys.exit(do_handle_alerts(args))

        elif o == '--notify':
            read_config_files(with_conf_d=True, validate_hosts=False)
            sys.exit(do_notify(args))

        elif o == '--real-time-checks':
            read_config_files(with_conf_d=True, validate_hosts=False)
            load_module("keepalive")
            load_module("real_time_checks")
            do_real_time_checks(args)
            sys.exit(0)

        elif o == '--create-rrd':
            read_config_files(with_conf_d=True, validate_hosts=False)
            load_module("rrd")
            do_create_rrd(args)
            done = True
        elif o == '--convert-rrds':
            read_config_files(with_conf_d=True)
            load_module("rrd")
            do_convert_rrds(args)
            done = True
        elif o == '--compress-history':
            load_module("compresslog")
            do_compress_history(args)
            done = True
        elif o in [ '-A', '--bake-agents' ]:
            if 'do_bake_agents' not in globals():
                bail_out("Agent baking is not implemented in your version of Check_MK. Sorry.")
            if args:
                hostnames = parse_hostname_list(args, with_clusters = False, with_foreign_hosts = True)
            else:
                hostnames = None
            do_bake_agents(hostnames)
            done = True

        elif o == '--cap':
            if 'do_cap' not in globals():
                bail_out("Agent packages are not supported by your version of Check_MK.")
            do_cap(args)
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
                        print "Cannot resolve hostname '%s'." % hostname
                        sys.exit(2)

            exit_status = do_check(hostname, ipaddress, check_types)

    output_profile()
    sys.exit(exit_status)

except MKTerminate, e:
    # At top level this exception means the process has been terminated without issues.
    sys.exit(0)

except (MKGeneralException, MKBailOut), e:
    sys.stderr.write("%s\n" % e)
    if opt_debug:
        raise
    sys.exit(3)

