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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os, sys, socket, time, getopt, glob, re, stat, py_compile, urllib, inspect
import subprocess

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
nagios_objects_file                = var_dir + '/check_mk_objects.cfg'
nagios_command_pipe_path           = '/usr/local/nagios/var/rw/nagios.cmd'
check_result_path                  = '/usr/local/nagios/var/spool/checkresults'
www_group                          = None # unset
nagios_startscript                 = '/etc/init.d/nagios'
nagios_binary                      = '/usr/sbin/nagios'
nagios_config_file                 = '/etc/nagios/nagios.cfg'
logwatch_notes_url                 = "/nagios/logwatch.php?host=%s&file=%s"
rrdcached_socket                   = None # used by prediction.py
rrd_path                           = None # used by prediction.py


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
}

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

known_vars = set(vars().keys())
known_vars.add('known_vars')
execfile(modules_dir + '/config.py')
config_variable_names = set(vars().keys()).difference(known_vars)

# at check time (and many of what is also needed at administration time).
try:
    modules = [ 'check_mk_base', 'discovery', 'snmp', 'agent_simulator', 'notify', 'prediction', 'cmc', 'inline_snmp', 'agent_bakery', 'cap' ]
    for module in modules:
        filename = modules_dir + "/" + module + ".py"
        if os.path.exists(filename):
            execfile(filename)

except Exception, e:
    sys.stderr.write("Cannot read file %s: %s\n" % (filename, e))
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
checkgroup_of                      = {} # groups of checks with compatible parametration
check_includes                     = {} # library files needed by checks
precompile_params                  = {} # optional functions for parameter precompilation, look at df for an example
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
# Do not read in the checks if check_mk is called as module
def load_checks():
    filelist = glob.glob(checks_dir + "/*")
    filelist.sort()

    # read local checks *after* shipped ones!
    if local_checks_dir:
        local_files = glob.glob(local_checks_dir + "/*")
        local_files.sort()
        filelist += local_files

    # read include files always first, but still in the sorted
    # order with local ones last (possibly overriding variables)
    filelist = [ f for f in filelist if f.endswith(".include") ] + \
               [ f for f in filelist if not f.endswith(".include") ]

    varname = None
    value = None
    ignored_variable_types = [ type(lambda: None), type(os) ]

    known_vars = set(globals().keys()) # track new configuration variables

    for f in filelist:
        if not f.endswith("~"): # ignore emacs-like backup files
            try:
                execfile(f, globals())
            except Exception, e:
                sys.stderr.write("Error in plugin file %s: %s\n" % (f, e))
                if opt_debug:
                    raise
                sys.exit(5)

    for varname, value in globals().iteritems():
        if varname[0] != '_' \
            and varname not in known_vars \
            and type(value) not in ignored_variable_types:
            config_variable_names.add(varname)

    # Now convert check_info to new format.
    convert_check_info()


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

    checks_sorted = check_info.items() + active_check_info.items()
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

def strip_tags(host_or_list):
    if type(host_or_list) == list:
        return [ strip_tags(h) for h in host_or_list ]
    else:
        return host_or_list.split("|")[0]

def tags_of_host(hostname):
    return hosttags.get(hostname, [])

# Check if a host fullfills the requirements of a tags
# list. The host must have all tags in the list, except
# for those negated with '!'. Those the host must *not* have!
# New in 1.1.13: a trailing + means a prefix match
def hosttags_match_taglist(hosttags, required_tags):
    for tag in required_tags:
        if len(tag) > 0 and tag[0] == '!':
            negate = True
            tag = tag[1:]
        else:
            negate = False

        if tag and tag[-1] == '+':
            tag = tag[:-1]
            matches = False
            for t in hosttags:
                if t.startswith(tag):
                    matches = True
                    break

        else:
            matches = (tag in hosttags)

        if matches == negate:
            return False

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

def is_tcp_host(hostname):
    return in_binary_hostlist(hostname, tcp_hosts)

def is_ping_host(hostname):
    return not is_snmp_host(hostname) and not is_tcp_host(hostname)

def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)

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
    else:
        command = 'snmpbulkwalk'

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
        else:
            raise MKGeneralException("Invalid SNMP credentials '%r' for host %s: must be string, 4-tuple or 6-tuple" % (credentials, hostname))

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

    portspec = snmp_port_spec(hostname)
    command = snmp_base_command(commandtype, hostname) + \
              " -On -OQ -Oe -Ot %s%s %s" % (ipaddress, portspec, oid_prefix)

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
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value

def get_single_oid(hostname, ipaddress, oid):
    # New in Check_MK 1.1.11: oid can end with ".*". In that case
    # we do a snmpgetnext and try to find an OID with the prefix
    # in question. The *cache* is working including the X, however.

    if oid[0] != '.':
        raise MKGeneralException("OID definition '%s' does not begin with ." % oid)

    global g_single_oid_hostname
    global g_single_oid_cache

    if g_single_oid_hostname != hostname:
        g_single_oid_hostname = hostname
        g_single_oid_cache = {}

    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    if opt_use_snmp_walk or is_usewalk_host(hostname):
        walk = get_stored_snmpwalk(hostname, oid)
        if len(walk) == 1:
            return walk[0][1]
        else:
            return None

    try:
        if has_inline_snmp and use_inline_snmp:
            value = inline_snmp_get_oid(hostname, oid)
        else:
            value = snmp_get_oid(hostname, ipaddress, oid)
    except:
        if opt_debug:
            raise
        value = None

    g_single_oid_cache[oid] = value
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


# clusternames (keys into dictionary) might be tagged :-(
# names of nodes not!
def is_cluster(hostname):
    for tagged_hostname, nodes in clusters.items():
        if hostname == strip_tags(tagged_hostname):
            return True
    return False

# If host is node of one or more clusters, return a list of the clusters
# (untagged). If not, return an empty list.
def clusters_of(hostname):
    return [ strip_tags(c) for c,n in clusters.items() if hostname in n ]

# Determine weather a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    the_clusters = clusters_of(hostname)
    if not the_clusters:
        return hostname

    cluster_mapping = service_extra_conf(hostname, servicedesc, clustered_services_mapping)
    if cluster_mapping:
        return cluster_mapping[0]

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

    # speed up multiple lookup of same host
    if use_cache and hostname in g_check_table_cache:
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

    def handle_entry(entry):
        if len(entry) == 3: # from autochecks
            hostlist = hostname
            checkname, item, params = entry
            tags = []
        elif len(entry) == 4:
            hostlist, checkname, item, params = entry
            tags = []
        elif len(entry) == 5:
            tags, hostlist, checkname, item, params = entry
            if type(tags) != list:
                raise MKGeneralException("Invalid entry '%r' in check table. First entry must be list of host tags." %
                                         (entry, ))

        else:
            raise MKGeneralException("Invalid entry '%r' in check table. It has %d entries, but must have 4 or 5." %
                                     (entry, len(entry)))

        # hostinfo list might be:
        # 1. a plain hostname (string)
        # 2. a list of hostnames (list of strings)
        # Hostnames may be tagged. Tags are removed.
        # In autochecks there are always single untagged hostnames.
        # We optimize for that. But: hostlist might be tagged hostname!
        if type(hostlist) == str:
            if hostlist != hostname:
                return # optimize most common case: hostname mismatch
            hostlist = [ strip_tags(hostlist) ]
        elif type(hostlist[0]) == str:
            hostlist = strip_tags(hostlist)
        elif hostlist != []:
            raise MKGeneralException("Invalid entry '%r' in check table. Must be single hostname or list of hostnames" % hostlist)

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
               in_extraconf_hostlist(hostlist, hostname):
            descr = service_description(checkname, item)
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
                descr = service_description(checkname, item)
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

    if use_cache:
        g_check_table_cache[hostname] = check_table

    if remove_duplicates and is_dual_host(hostname):
        return remove_duplicate_checks(check_table)
    else:
        return check_table


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
            deps_fullfilled = True
            for dep in check[4]: # deps
                if dep in unsorted_descrs:
                    deps_fullfilled = False
                    break
            if deps_fullfilled:
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
failed_ip_lookups = []

# Determine the IP address of a host
def lookup_ipaddress(hostname):
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if fake_dns:
        return fake_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    elif simulation_mode or opt_use_snmp_walk or \
         (is_usewalk_host(hostname) and is_snmp_host(hostname)):
        return "127.0.0.1"

    # Now check, if IP address is hard coded by the user
    ipa = ipaddresses.get(hostname)
    if ipa:
        return ipa

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if in_binary_hostlist(hostname, dyndns_hosts):
        return hostname

    # Address has already been resolved in prior call to this function?
    if hostname in g_dns_cache:
        return g_dns_cache[hostname]

    # Prepare file based fall-back DNS cache in case resolution fails
    init_ip_lookup_cache()

    cached_ip = g_ip_lookup_cache.get(hostname)
    if cached_ip and use_dns_cache:
        g_dns_cache[hostname] = cached_ip
        return cached_ip

    # Now do the actual DNS lookup
    try:
        ipa = socket.gethostbyname(hostname)

        # Update our cached address if that has changed or was missing
        if ipa != cached_ip:
            if opt_verbose:
                print "Updating DNS cache for %s: %s" % (hostname, ipa)
            g_ip_lookup_cache[hostname] = ipa
            write_ip_lookup_cache()

        g_dns_cache[hostname] = ipa # Update in-memory-cache
        return ipa

    except:
        # DNS failed. Use cached IP address if present, even if caching
        # is disabled.
        if cached_ip:
            g_dns_cache[hostname] = cached_ip
            return cached_ip
        else:
            g_dns_cache[hostname] = None
            raise

def init_ip_lookup_cache():
    global g_ip_lookup_cache
    if g_ip_lookup_cache is None:
        try:
            g_ip_lookup_cache = eval(file(var_dir + '/ipaddresses.cache').read())
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

    if opt_verbose:
        print "Updating DNS cache..."
    for hostname in all_active_hosts() + all_active_clusters():
        if opt_verbose:
            sys.stdout.write("%s..." % hostname)
            sys.stdout.flush()
        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        try:
            ip = lookup_ipaddress(hostname)
            if opt_verbose:
                sys.stdout.write("%s\n" % ip)
            updated += 1
        except Exception, e:
            failed.append(hostname)
            if opt_verbose:
                sys.stdout.write("lookup failed: %s\n" % e)
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


def service_description(check_type, item):
    if check_type not in check_info:
        if item:
            return "Unimplmented check %s / %s" % (check_type, item)
        else:
            return "Unimplemented check %s" % check_type

        # raise MKGeneralException("Unknown check type '%s'.\n"
        #                         "Please use check_mk -L for a list of all check types.\n" % check_type)

    # use user-supplied service description, of available
    descr_format = service_descriptions.get(check_type)
    if not descr_format:
        # handle renaming for backward compatibility
        if check_type in old_service_descriptions and \
           check_type not in use_new_descriptions_for:
           descr_format = old_service_descriptions[check_type]
        else:
            descr_format = check_info[check_type]["service_description"]

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.

    if type(item) == str:
        # Remove characters from item name that are banned by Nagios
        item_safe = sanitize_service_description(item)
        if "%s" not in descr_format:
            descr_format += " %s"
        return (descr_format % (item_safe,)).strip()
    if type(item) == int or type(item) == long:
        if "%s" not in descr_format:
            descr_format += " %s"
        return (descr_format % (item,)).strip()
    else:
        return descr_format.strip()


# Get rules for piggyback translation for that hostname
def get_piggyback_translation(hostname):
    rules = host_extra_conf(hostname, piggyback_translation)
    translations = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


#.
#   .--Config Ouptut-------------------------------------------------------.
#   |    ____             __ _          ___              _         _       |
#   |   / ___|___  _ __  / _(_) __ _   / _ \ _   _ _ __ | |_ _   _| |_     |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | | | | | '_ \| __| | | | __|    |
#   |  | |__| (_) | | | |  _| | (_| | | |_| | |_| | |_) | |_| |_| | |_     |
#   |   \____\___/|_| |_|_| |_|\__, |  \___/ \__,_| .__/ \__|\__,_|\__|    |
#   |                          |___/              |_|                      |
#   +----------------------------------------------------------------------+
#   | Output an ASCII configuration file for the monitoring core.          |
#   '----------------------------------------------------------------------'

def make_utf8(x):
    if type(x) == unicode:
        return x.encode('utf-8')
    else:
        return x

def output_conf_header(outfile):
    outfile.write("""#
# Created by Check_MK. Do not edit.
#

""")

# Returns a list of all host names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_physical_hosts():
    return strip_tags(all_hosts)

def all_active_hosts():
    return filter_active_hosts(all_hosts)

def all_active_clusters():
    return filter_active_hosts(clusters.keys())

def filter_active_hosts(hostlist):
    if only_hosts == None and distributed_wato_site == None:
        return strip_tags(hostlist)
    elif only_hosts == None:
        return [ hostname for hostname in strip_tags(hostlist)
                 if host_is_member_of_site(hostname, distributed_wato_site) ]
    elif distributed_wato_site == None:
        return [ hostname for hostname in strip_tags(hostlist)
                 if in_binary_hostlist(hostname, only_hosts) ]
    else:
        site_tag = "site:" + distributed_wato_site
        return [ hostname for hostname in strip_tags(hostlist)
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
        valid_hosts = all_configured_physical_hosts()
    else:
        valid_hosts = all_active_hosts()
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
            if pss in all_hosts_untagged:
                used_parents.append(pss)
    return used_parents

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

    elif value in [ "ping", "smart" ]:
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



def check_icmp_arguments_of(hostname):
    values = host_extra_conf(hostname, ping_levels)
    levels = {}
    for value in values[::-1]: # make first rules have precedence
        levels.update(value)
    if len(levels) == 0:
        return ""

    args = []
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
            raise MKGeneralException("Invalid entry '%r' in service dependencies: must have 3 or 4 entries" % entry)

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


def host_extra_conf(hostname, conf):
    items = []
    if len(conf) == 1 and conf[0] == "":
        sys.stderr.write('WARNING: deprecated entry [ "" ] in host configuration list\n')

    for entry in conf:
        entry, rule_options = get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 2:
            item, hostlist = entry
            tags = []
        elif len(entry) == 3:
            item, tags, hostlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in host configuration list: must have 2 or 3 entries" % (entry,))

        # Note: hostname may be True. This is an unknown generic host, that has
        # no tags and that does not match any positive criteria in any rule.
        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname):
            items.append(item)
    return items

def host_extra_conf_merged(hostname, conf):
    rule_dict = {}
    for rule in host_extra_conf(hostname, conf):
        for key, value in rule.items():
            rule_dict.setdefault(key, value)
    return rule_dict

def in_binary_hostlist(hostname, conf):
    # if we have just a list of strings just take it as list of (may be tagged) hostnames
    if len(conf) > 0 and type(conf[0]) == str:
        return hostname in strip_tags(conf)

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
            MKGeneralException("Invalid entry '%r' in host configuration list: must be tupel with 1 or 2 entries" % (entry,))

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


def all_matching_hosts(tags, hostlist):
    matching = set([])
    for taggedhost in all_hosts + clusters.keys():
        parts = taggedhost.split("|")
        hostname = parts[0]
        hosttags = parts[1:]

        if hosttags_match_taglist(hosttags, tags) and \
           in_extraconf_hostlist(hostlist, hostname):
           matching.add(hostname)
    return matching

g_converted_rulesets_cache = {}

def convert_service_ruleset(ruleset):
    new_rules = []
    for rule in ruleset:
        rule, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        if len(rule) == 3:
            item, hostlist, servlist = rule
            tags = []
        elif len(rule) == 4:
            item, tags, hostlist, servlist = rule
        else:
            raise MKGeneralException("Invalid rule '%r' in service configuration list: must have 3 or 4 elements" % (rule,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist)
        new_rules.append((item, hosts, servlist))

    g_converted_rulesets_cache[id(ruleset)] = new_rules


def serviceruleset_is_converted(ruleset):
    return id(ruleset) in g_converted_rulesets_cache


# Compute outcome of a service rule set that has an item
def service_extra_conf(hostname, service, ruleset):
    if not serviceruleset_is_converted(ruleset):
        convert_service_ruleset(ruleset)

    entries = []
    for item, hosts, servlist in g_converted_rulesets_cache[id(ruleset)]:
        if hostname in hosts and in_extraconf_servicelist(servlist, service):
            entries.append(item)
    return entries


def convert_boolean_service_ruleset(ruleset):
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
            raise MKGeneralException("Invalid entry '%r' in configuration: must have 2 or 3 elements" % (entry,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist)
        new_rules.append((negate, hosts, servlist))

    g_converted_rulesets_cache[id(ruleset)] = new_rules


# Compute outcome of a service rule set that just say yes/no
def in_boolean_serviceconf_list(hostname, service_description, ruleset):
    if not serviceruleset_is_converted(ruleset):
        convert_boolean_service_ruleset(ruleset)

    for negate, hosts, servlist in g_converted_rulesets_cache[id(ruleset)]:
        if hostname in hosts and \
           in_extraconf_servicelist(servlist, service_description):
            return not negate
    return False # no match. Do not ignore



# Entries in list are (tagged) hostnames that must equal the
# (untagged) hostname. Expressions beginning with ! are negated: if
# they match, the item is excluded from the list. Expressions beginning
# withy ~ are treated as Regular Expression. Also the three
# special tags '@all', '@clusters', '@physical' are allowed.
def in_extraconf_hostlist(hostlist, hostname):

    # Migration help: print error if old format appears in config file
    if len(hostlist) == 1 and hostlist[0] == "":
        raise MKGeneralException('Invalid empty entry [ "" ] in configuration')

    for hostentry in hostlist:
        if len(hostentry) == 0:
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

        hostentry = strip_tags(hostentry)
        try:
            if not use_regex and hostname == hostentry:
                return not negate
            # Handle Regex. Note: hostname == True -> generic unknown host
            elif use_regex and hostname != True and regex(hostentry).match(hostname):
                return not negate
        except MKGeneralException:
            if opt_debug:
                raise

    return False


def in_extraconf_servicelist(list, item):
    for pattern in list:
        # Allow negation of pattern with prefix '!'
        if len(pattern) > 0 and pattern[0] == '!':
            pattern = pattern[1:]
            negate = True
        else:
            negate = False

        if regex(pattern).match(item):
            return not negate

    # no match in list -> negative answer
    return False


def create_nagios_config(outfile = sys.stdout, hostnames = None):
    global hostgroups_to_define
    hostgroups_to_define = set([])
    global servicegroups_to_define
    servicegroups_to_define = set([])
    global contactgroups_to_define
    contactgroups_to_define = set([])
    global checknames_to_define
    checknames_to_define = set([])
    global active_checks_to_define
    active_checks_to_define = set([])
    global custom_commands_to_define
    custom_commands_to_define = set([])
    global hostcheck_commands_to_define
    hostcheck_commands_to_define = []

    if host_notification_periods != []:
        raise MKGeneralException("host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead.")

    if summary_host_notification_periods != []:
        raise MKGeneralException("summary_host_notification_periods is not longer supported. Please use extra_summary_host_conf['notification_period'] instead.")

    if service_notification_periods != []:
        raise MKGeneralException("service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead.")

    if summary_service_notification_periods != []:
        raise MKGeneralException("summary_service_notification_periods is not longer supported. Please use extra_summary_service_conf['notification_period'] instead.")

    # Map service_period to _SERVICE_PERIOD. This field das not exist in Nagios/Icinga.
    # The CMC has this field natively.
    if "service_period" in extra_host_conf:
        extra_host_conf["_SERVICE_PERIOD"] = extra_host_conf["service_period"]
        del extra_host_conf["service_period"]
    if "service_period" in extra_service_conf:
        extra_service_conf["_SERVICE_PERIOD"] = extra_service_conf["service_period"]
        del extra_service_conf["service_period"]

    output_conf_header(outfile)
    if hostnames == None:
        hostnames = all_hosts_untagged + all_active_clusters()

    for hostname in hostnames:
        create_nagios_config_host(outfile, hostname)

    create_nagios_config_contacts(outfile, hostnames)
    create_nagios_config_hostgroups(outfile)
    create_nagios_config_servicegroups(outfile)
    create_nagios_config_contactgroups(outfile)
    create_nagios_config_commands(outfile)
    create_nagios_config_timeperiods(outfile)

    if extra_nagios_conf:
        outfile.write("\n# extra_nagios_conf\n\n")
        outfile.write(extra_nagios_conf)

def create_nagios_config_host(outfile, hostname):
    outfile.write("\n# ----------------------------------------------------\n")
    outfile.write("# %s\n" % hostname)
    outfile.write("# ----------------------------------------------------\n")
    if generate_hostconf:
        create_nagios_hostdefs(outfile, hostname)
    create_nagios_servicedefs(outfile, hostname)

def create_nagios_hostdefs(outfile, hostname):
    is_clust = is_cluster(hostname)

    # Determine IP address. For cluster hosts this is optional.
    # A cluster might have or not have a service ip address.
    try:
        ip = lookup_ipaddress(hostname)
    except:
        if not is_clust:
            if ignore_ip_lookup_failures:
                failed_ip_lookups.append(hostname)
            else:
                raise MKGeneralException("Cannot determine ip address of %s. Please add to ipaddresses." % hostname)
        ip = None

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    alias = hostname
    outfile.write("\ndefine host {\n")
    outfile.write("  host_name\t\t\t%s\n" % hostname)
    outfile.write("  use\t\t\t\t%s\n" % (is_clust and cluster_template or host_template))
    outfile.write("  address\t\t\t%s\n" % (ip and make_utf8(ip) or "0.0.0.0"))
    outfile.write("  _TAGS\t\t\t\t%s\n" % " ".join(tags_of_host(hostname)))

    # Host check command might differ from default
    command = host_check_command(hostname, ip, is_clust)
    if command:
        outfile.write("  check_command\t\t\t%s\n" % command)

    # WATO folder path
    path = host_paths.get(hostname)
    if path:
        outfile.write("  _FILENAME\t\t\t%s\n" % path)

    # Host groups: If the host has no hostgroups it gets the default
    # hostgroup (Nagios requires each host to be member of at least on
    # group.
    hgs = hostgroups_of(hostname)
    hostgroups = ",".join(hgs)
    if len(hgs) == 0:
        hostgroups = default_host_group
        hostgroups_to_define.add(default_host_group)
    elif define_hostgroups:
        hostgroups_to_define.update(hgs)
    outfile.write("  hostgroups\t\t\t%s\n" % make_utf8(hostgroups))

    # Contact groups
    cgrs = host_contactgroups_of([hostname])
    if len(cgrs) > 0:
        outfile.write("  contact_groups\t\t%s\n" % make_utf8(",".join(cgrs)))
        contactgroups_to_define.update(cgrs)

    # Get parents manually defined via extra_host_conf["parents"]. Only honor
    # variable "parents" and implicit parents if this setting is empty
    extra_conf_parents = host_extra_conf(hostname, extra_host_conf.get("parents", []))

    # Parents for non-clusters
    if not extra_conf_parents and not is_clust:
        parents_list = parents_of(hostname)
        if len(parents_list) > 0:
            outfile.write("  parents\t\t\t%s\n" % (",".join(parents_list)))

    # Special handling of clusters
    if is_clust:
        nodes = nodes_of(hostname)
        for node in nodes:
            if node not in all_hosts_untagged:
                raise MKGeneralException("Node %s of cluster %s not in all_hosts." % (node, hostname))
        node_ips = [ lookup_ipaddress(h) for h in nodes ]
        alias = "cluster of %s" % ", ".join(nodes)
        outfile.write("  _NODEIPS\t\t\t%s\n" % " ".join(node_ips))
        if not extra_conf_parents:
            outfile.write("  parents\t\t\t%s\n" % ",".join(nodes))

    # Output alias, but only if it's not defined in extra_host_conf
    alias = alias_of(hostname, None)
    if alias == None:
        outfile.write("  alias\t\t\t\t%s\n" % alias)
    else:
        alias = make_utf8(alias)


    # Custom configuration last -> user may override all other values
    outfile.write(make_utf8(extra_host_conf_of(hostname)))

    outfile.write("}\n")

    #   ____
    #  |___ \
    #   __) |
    #  / __/
    #  |_____|  2. summary hosts

    if host_is_aggregated(hostname):
        outfile.write("\ndefine host {\n")
        outfile.write("  host_name\t\t\t%s\n" % summary_hostname(hostname))
        outfile.write("  use\t\t\t\t%s-summary\n" % (is_clust and cluster_template or host_template))
        outfile.write("  alias\t\t\t\tSummary of %s\n" % alias)
        outfile.write("  address\t\t\t%s\n" % (ip and ip or "0.0.0.0"))
        outfile.write("  _TAGS\t\t\t\t%s\n" % " ".join(tags_of_host(hostname)))
        outfile.write("  __REALNAME\t\t\t%s\n" % hostname)
        outfile.write("  parents\t\t\t%s\n" % hostname)

        if path:
            outfile.write("  _FILENAME\t\t\t%s\n" % path)

        hgs = summary_hostgroups_of(hostname)
        hostgroups = ",".join(hgs)
        if len(hgs) == 0:
            hostgroups = default_host_group
            hostgroups_to_define.add(default_host_group)
        elif define_hostgroups:
            hostgroups_to_define.update(hgs)
        outfile.write("  hostgroups\t\t\t+%s\n" % hostgroups)

        # host gets same contactgroups as real host
        if len(cgrs) > 0:
            outfile.write("  contact_groups\t\t+%s\n" % make_utf8(",".join(cgrs)))

        if is_clust:
            outfile.write("  _NODEIPS\t\t\t%s\n" % " ".join(node_ips))
        outfile.write(extra_summary_host_conf_of(hostname))
        outfile.write("}\n")
    outfile.write("\n")

def create_nagios_servicedefs(outfile, hostname):
    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services


    def do_omit_service(hostname, description):
        if service_ignored(hostname, None, description):
            return True
        if hostname != host_of_clustered_service(hostname, description):
            return True
        return False

    def get_dependencies(hostname,servicedesc):
        result = ""
        for dep in service_deps(hostname, servicedesc):
            result += """
define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t%s
  dependent_host_name\t%s
  dependent_service_description %s
}\n
""" % (service_dependency_template, hostname, dep, hostname, servicedesc)

        return result

    host_checks = get_check_table(hostname, remove_duplicates=True).items()
    host_checks.sort() # Create deterministic order
    aggregated_services_conf = set([])
    do_aggregation = host_is_aggregated(hostname)
    have_at_least_one_service = False
    used_descriptions = {}
    for ((checkname, item), (params, description, deps)) in host_checks:
        if checkname not in check_info:
            continue # simply ignore missing checks

        # Make sure, the service description is unique on this host
        if description in used_descriptions:
            cn, it = used_descriptions[description]
            raise MKGeneralException(
                    "ERROR: Duplicate service description '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = %s, item = %r\n" %
                    (description, hostname, cn, it, checkname, item))

        else:
            used_descriptions[description] = ( checkname, item )
        if check_info[checkname].get("has_perfdata", False):
            template = passive_service_template_perf
        else:
            template = passive_service_template

        # Hardcoded for logwatch check: Link to logwatch.php
        if checkname == "logwatch":
            logwatch = "  notes_url\t\t\t" + (logwatch_notes_url % (urllib.quote(hostname), urllib.quote(item))) + "\n"
        else:
            logwatch = "";

        # Services Dependencies
        for dep in deps:
            outfile.write("define servicedependency {\n"
                         "    use\t\t\t\t%s\n"
                         "    host_name\t\t\t%s\n"
                         "    service_description\t%s\n"
                         "    dependent_host_name\t%s\n"
                         "    dependent_service_description %s\n"
                         "}\n\n" % (service_dependency_template, hostname, dep, hostname, description))


        # Handle aggregated services. If this service belongs to an aggregation,
        # remember, that the aggregated service must be configured. We cannot
        # do this here, because each aggregated service must occur only once
        # in the configuration.
        if do_aggregation:
            asn = aggregated_service_name(hostname, description)
            if asn != "":
                aggregated_services_conf.add(asn)

        # Add the check interval of either the Check_MK service or
        # (if configured) the snmp_check_interval for snmp based checks
        check_interval = 1 # default hardcoded interval
        # Customized interval of Check_MK service
        values = service_extra_conf(hostname, "Check_MK", extra_service_conf.get('check_interval', []))
        if values:
            try:
                check_interval = int(values[0])
            except:
                check_interval = float(values[0])
        value = check_interval_of(hostname, checkname)
        if value is not None:
            check_interval = value

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\t%s
  check_interval\t\t%d
%s%s  check_command\t\t\tcheck_mk-%s
}

""" % ( template, hostname, description, check_interval, logwatch,
        extra_service_conf_of(hostname, description), checkname ))

        checknames_to_define.add(checkname)
        have_at_least_one_service = True


    # Now create definitions of the aggregated services for this host
    if do_aggregation and service_aggregations:
        outfile.write("\n# Aggregated services\n\n")

    aggr_descripts = aggregated_services_conf
    if aggregate_check_mk and host_is_aggregated(hostname) and have_at_least_one_service:
        aggr_descripts.add("Check_MK")

    # If a ping-only-host is aggregated, the summary host gets it's own
    # copy of the ping - as active check. We cannot aggregate the result
    # from the ping of the real host since no Check_MK is running during
    # the check.
    elif host_is_aggregated(hostname) and not have_at_least_one_service:
        outfile.write("""
define service {
  use\t\t\t\t%s
%s  host_name\t\t\t%s
}

""" % (pingonly_template, extra_service_conf_of(hostname, "PING"), summary_hostname(hostname)))

    for description in aggr_descripts:
        sergr = service_extra_conf(hostname, description, summary_service_groups)
        if len(sergr) > 0:
            sg = "  service_groups\t\t\t+" + make_utf8(",".join(sergr)) + "\n"
            if define_servicegroups:
                servicegroups_to_define.update(sergr)
        else:
            sg = ""

        sercgr = service_extra_conf(hostname, description, summary_service_contactgroups)
        contactgroups_to_define.update(sercgr)
        if len(sercgr) > 0:
            scg = "  contact_groups\t\t\t+" + ",".join(sercgr) + "\n"
        else:
            scg = ""

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s%s%s  service_description\t\t%s
}

""" % ( summary_service_template, summary_hostname(hostname), sg, scg,
extra_summary_service_conf_of(hostname, description), description  ))

    # Active check for check_mk
    if have_at_least_one_service:
        outfile.write("""
# Active checks

define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s  service_description\t\tCheck_MK
}
""" % (active_service_template, hostname, extra_service_conf_of(hostname, "Check_MK")))

    # legacy checks via legacy_checks
    legchecks = host_extra_conf(hostname, legacy_checks)
    if len(legchecks) > 0:
        outfile.write("\n\n# Legacy checks\n")
    for command, description, has_perfdata in legchecks:
        description = sanitize_service_description(description)
        if do_omit_service(hostname, description):
            continue

        if description in used_descriptions:
            cn, it = used_descriptions[description]
            raise MKGeneralException(
                    "ERROR: Duplicate service description (legacy check) '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = legacy(%s), item = None\n" %
                    (description, hostname, cn, it, command))

        else:
            used_descriptions[description] = ( "legacy(" + command + ")", description )

        extraconf = extra_service_conf_of(hostname, description)
        if has_perfdata:
            template = "check_mk_perf,"
        else:
            template = ""
        outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t1
%s}
""" % (template, hostname, make_utf8(description), simulate_command(command), extraconf))

        # write service dependencies for legacy checks
        outfile.write(get_dependencies(hostname,description))

    # legacy checks via active_checks
    actchecks = []
    needed_commands = []
    for acttype, rules in active_checks.items():
        entries = host_extra_conf(hostname, rules)
        if entries:
            active_checks_to_define.add(acttype)
            act_info = active_check_info[acttype]
            for params in entries:
                actchecks.append((acttype, act_info, params))

    if actchecks:
        outfile.write("\n\n# Active checks\n")
        for acttype, act_info, params in actchecks:
            # Make hostname available as global variable in argument functions
            global g_hostname
            g_hostname = hostname

            has_perfdata = act_info.get('has_perfdata', False)
            description = sanitize_service_description(
                 act_info["service_description"](params)
                 .replace('$HOSTNAME$', g_hostname))

            if do_omit_service(hostname, description):
                continue

            # compute argument, and quote ! and \ for Nagios
            args = act_info["argument_function"](params).replace("\\", "\\\\").replace("!", "\\!")

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                if cn == "active(%s)" % acttype:
                    continue

                raise MKGeneralException(
                        "ERROR: Duplicate service description (active check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = active(%s), item = None\n" %
                        (description, hostname, cn, it, acttype))

            else:
                used_descriptions[description] = ( "active(" + acttype + ")", description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = extra_service_conf_of(hostname, description)
            command = "check_mk_active-%s!%s" % (acttype, args)
            outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t1
%s}
""" % (template, hostname, make_utf8(description), make_utf8(simulate_command(command)), extraconf))

            # write service dependencies for active checks
            outfile.write(get_dependencies(hostname,description))

    # Legacy checks via custom_checks
    custchecks = host_extra_conf(hostname, custom_checks)
    if custchecks:
        outfile.write("\n\n# Custom checks\n")
        for entry in custchecks:
            # entries are dicts with the following keys:
            # "service_description"        Service description to use
            # "command_line"  (optional)   Unix command line for executing the check
            #                              If this is missing, we create a passive check
            # "command_name"  (optional)   Name of Monitoring command to define. If missing,
            #                              we use "check-mk-custom"
            # "has_perfdata"  (optional)   If present and True, we activate perf_data
            description = sanitize_service_description(entry["service_description"])
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if do_omit_service(hostname, description):
                continue

            if command_line:
                command_line = autodetect_plugin(command_line).replace("\\", "\\\\")

            if "freshness" in entry:
                freshness = "  check_freshness\t\t1\n" + \
                            "  freshness_threshold\t\t%d\n" % (60 * entry["freshness"]["interval"])
                command_line = "echo %s && exit %d" % (
                       quote_nagios_string(entry["freshness"]["output"]), entry["freshness"]["state"])
            else:
                freshness = ""

            custom_commands_to_define.add(command_name)

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one.
                if cn == "custom(%s)" % command_name:
                    continue
                raise MKGeneralException(
                        "ERROR: Duplicate service description (custom check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = custom(%s), item = %r\n" %
                        (description, hostname, cn, it, command_name, description))
            else:
                used_descriptions[description] = ( "custom(%s)" % command_name, description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = extra_service_conf_of(hostname, description)
            command = "%s!%s" % (command_name, command_line)
            outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t%d
%s%s}
""" % (template, hostname, make_utf8(description), simulate_command(command),
       (command_line and not freshness) and 1 or 0, extraconf, freshness))

            # write service dependencies for custom checks
            outfile.write(get_dependencies(hostname,description))

    # FIXME: Remove old name one day
    service_discovery_name = 'Check_MK inventory'
    if 'cmk-inventory' in use_new_descriptions_for:
        service_discovery_name = 'Check_MK Discovery'

    # Inventory checks - if user has configured them.
    if inventory_check_interval \
        and not service_ignored(hostname, None, service_discovery_name) \
        and not "ping" in tags_of_host(hostname):
        outfile.write("""
define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  normal_check_interval\t\t%d
  retry_check_interval\t\t%d
%s  service_description\t\t%s
}
""" % (inventory_check_template, hostname, inventory_check_interval,
       inventory_check_interval,
       extra_service_conf_of(hostname, service_discovery_name),
       service_discovery_name))

        if have_at_least_one_service:
            outfile.write("""
define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\tCheck_MK
  dependent_host_name\t\t%s
  dependent_service_description\t%s
}
""" % (service_dependency_template, hostname, hostname, service_discovery_name))

    # Levels for host check
    if is_cluster(hostname):
        ping_command = 'check-mk-ping-cluster'
    else:
        ping_command = 'check-mk-ping'

    # No check_mk service, no legacy service -> create PING service
    if not have_at_least_one_service and not legchecks and not actchecks and not custchecks:
        outfile.write("""
define service {
  use\t\t\t\t%s
  check_command\t\t\t%s!%s
%s  host_name\t\t\t%s
}

""" % (pingonly_template, ping_command, check_icmp_arguments_of(hostname), extra_service_conf_of(hostname, "PING"), hostname))

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

def simulate_command(command):
    if simulation_mode:
        custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    else:
        return command

def create_nagios_config_hostgroups(outfile):
    if define_hostgroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Host groups (controlled by define_hostgroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        hgs = list(hostgroups_to_define)
        hgs.sort()
        for hg in hgs:
            try:
                alias = define_hostgroups[hg]
            except:
                alias = hg
            outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (make_utf8(hg), make_utf8(alias)))

    # No creation of host groups but we need to define
    # default host group
    elif default_host_group in hostgroups_to_define:
        outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\tCheck_MK default hostgroup
}
""" % default_host_group)


def create_nagios_config_servicegroups(outfile):
    if define_servicegroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Service groups (controlled by define_servicegroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        sgs = list(servicegroups_to_define)
        sgs.sort()
        for sg in sgs:
            try:
                alias = define_servicegroups[sg]
            except:
                alias = sg
            outfile.write("""
define servicegroup {
  servicegroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (make_utf8(sg), make_utf8(alias)))

def create_nagios_config_contactgroups(outfile):
    if define_contactgroups:
        cgs = list(contactgroups_to_define)
        cgs.sort()
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Contact groups (controlled by define_contactgroups)\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        for name in cgs:
            if type(define_contactgroups) == dict:
                alias = define_contactgroups.get(name, name)
            else:
                alias = name
            outfile.write("\ndefine contactgroup {\n"
                    "  contactgroup_name\t\t%s\n"
                    "  alias\t\t\t\t%s\n" % (make_utf8(name), make_utf8(alias)))
            members = contactgroup_members.get(name)
            if members:
                outfile.write("  members\t\t\t%s\n" % ",".join(members))
            outfile.write("}\n")


def create_nagios_config_commands(outfile):
    if generate_dummy_commands:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Dummy check commands and active check commands\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        for checkname in checknames_to_define:
            outfile.write("""define command {
  command_name\t\t\tcheck_mk-%s
  command_line\t\t\t%s
}

""" % ( checkname, dummy_check_commandline ))

    # active_checks
    for acttype in active_checks_to_define:
        act_info = active_check_info[acttype]
        outfile.write("""define command {
  command_name\t\t\tcheck_mk_active-%s
  command_line\t\t\t%s
}

""" % ( acttype, act_info["command_line"]))

    # custom_checks
    for command_name in custom_commands_to_define:
        outfile.write("""define command {
  command_name\t\t\t%s
  command_line\t\t\t$ARG1$
}

""" % command_name)

    # custom host checks
    for command_name, command_line in hostcheck_commands_to_define:
        outfile.write("""define command {
  command_name\t\t\t%s
  command_line\t\t\t%s
}

""" % (command_name, command_line))


def create_nagios_config_timeperiods(outfile):
    if len(timeperiods) > 0:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Timeperiod definitions (controlled by variable 'timeperiods')\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        tpnames = timeperiods.keys()
        tpnames.sort()
        for name in tpnames:
            tp = timeperiods[name]
            outfile.write("define timeperiod {\n  timeperiod_name\t\t%s\n" % name)
            if "alias" in tp:
                outfile.write("  alias\t\t\t\t%s\n" % make_utf8(tp["alias"]))
            for key, value in tp.items():
                if key not in [ "alias", "exclude" ]:
                    times = ",".join([ ("%s-%s" % (fr, to)) for (fr, to) in value ])
                    if times:
                        outfile.write("  %-20s\t\t%s\n" % (key, times))
            if "exclude" in tp:
                outfile.write("  exclude\t\t\t%s\n" % ",".join(tp["exclude"]))
            outfile.write("}\n\n")

def create_nagios_config_contacts(outfile, hostnames):
    if len(contacts) > 0:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Contact definitions (controlled by variable 'contacts')\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        cnames = contacts.keys()
        cnames.sort()
        for cname in cnames:
            contact = contacts[cname]
            # Create contact groups in nagios, even when they are empty. This is needed
            # for RBN to work correctly when using contactgroups as recipients which are
            # not assigned to any host
            contactgroups_to_define.update(contact.get("contactgroups", []))
            # If the contact is in no contact group or all of the contact groups
            # of the contact have neither hosts nor services assigned - in other
            # words if the contact is not assigned to any host or service, then
            # we do not create this contact in Nagios. It's useless and will produce
            # warnings.
            cgrs = [ cgr for cgr in contact.get("contactgroups", []) if cgr in contactgroups_to_define ]
            if not cgrs:
                continue

            outfile.write("define contact {\n  contact_name\t\t\t%s\n" % cname)
            if "alias" in contact:
                outfile.write("  alias\t\t\t\t%s\n" % make_utf8(contact["alias"]))
            if "email" in contact:
                outfile.write("  email\t\t\t\t%s\n" % contact["email"])
            if "pager" in contact:
                outfile.write("  pager\t\t\t\t%s\n" % contact["pager"])
            if enable_rulebased_notifications:
                not_enabled = False
            else:
                not_enabled = contact.get("notifications_enabled", True)

            for what in [ "host", "service" ]:
                no = contact.get(what + "_notification_options", "")
                if not no or not not_enabled:
                    outfile.write("  %s_notifications_enabled\t0\n" % what)
                    no = "n"
                outfile.write("  %s_notification_options\t%s\n" % (what, ",".join(list(no))))
                outfile.write("  %s_notification_period\t%s\n" % (what, contact.get("notification_period", "24X7")))
                outfile.write("  %s_notification_commands\t%s\n" % (what, contact.get("%s_notification_commands" % what, "check-mk-notify")))
            # Add custom macros
            for macro in [ m for m in contact.keys() if m.startswith('_') ]:
                outfile.write("  %s\t%s\n" % ( macro, contact[macro] ))

            outfile.write("  contactgroups\t\t\t%s\n" % ", ".join(cgrs))
            outfile.write("}\n\n")

    if enable_rulebased_notifications and hostnames:
        outfile.write(
            "# Needed for rule based notifications\n"
            "define contact {\n"
            "  contact_name\t\t\tcheck-mk-notify\n"
            "  alias\t\t\t\tContact for rule based notifications\n"
            "  host_notification_options\td,u,r,f,s\n"
            "  service_notification_options\tu,c,w,r,f,s\n"
            "  host_notification_period\t24X7\n"
            "  service_notification_period\t24X7\n"
            "  host_notification_commands\tcheck-mk-notify\n"
            "  service_notification_commands\tcheck-mk-notify\n"
            "  contactgroups\t\t\tcheck-mk-notify\n"
            "}\n\n");


# Quote string for use in a nagios command execution.
# Please note that also quoting for ! and \ vor Nagios
# itself takes place here.
def quote_nagios_string(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "'\"'\"'").replace('!', '\\!') + "'"

#.
#   .--Precompile----------------------------------------------------------.
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Precompiling creates on dedicated Python file per host, which just   |
#   | contains that code and information that is needed for executing all  |
#   | checks of that host. Also static data that cannot change during the  |
#   | normal monitoring process is being precomputed and hard coded. This  |
#   | all saves substantial CPU ressources as opposed to running Check_MK  |
#   | in adhoc mode (about 75%).                                           |
#   '----------------------------------------------------------------------'

# Find files to be included in precompile host check for a certain
# check (for example df or mem.used). In case of checks with a period
# (subchecks) we might have to include both "mem" and "mem.used". The
# subcheck *may* be implemented in a separate file.
def find_check_plugins(checktype):
    if '.' in checktype:
        candidates = [ checktype.split('.')[0], checktype ]
    else:
        candidates = [ checktype ]

    paths = []
    for candidate in candidates:
        if local_checks_dir:
            filename = local_checks_dir + "/" + candidate
            if os.path.exists(filename):
                paths.append(filename)
                continue

        filename = checks_dir + "/" + candidate
        if os.path.exists(filename):
            paths.append(filename)

    return paths

def get_precompiled_check_table(hostname):
    host_checks = get_sorted_check_table(hostname, remove_duplicates=True)
    precomp_table = []
    for checktype, item, params, description, deps in host_checks:
        aggr_name = aggregated_service_name(hostname, description)
        # some checks need precompilation of parameters
        precomp_func = precompile_params.get(checktype)
        if precomp_func:
            params = precomp_func(hostname, item, params)
        precomp_table.append((checktype, item, params, description, aggr_name)) # deps not needed while checking
    return precomp_table

def precompile_hostchecks():
    if not os.path.exists(precompiled_hostchecks_dir):
        os.makedirs(precompiled_hostchecks_dir)
    for host in all_active_hosts() + all_active_clusters():
        try:
            precompile_hostcheck(host)
        except Exception, e:
            if opt_debug:
                raise
            sys.stderr.write("Error precompiling checks for host %s: %s\n" % (host, e))
            sys.exit(5)

# read python file and strip comments
g_stripped_file_cache = {}
def stripped_python_file(filename):
    if filename in g_stripped_file_cache:
        return g_stripped_file_cache[filename]
    a = ""
    for line in file(filename):
        l = line.strip()
        if l == "" or l[0] != '#':
            a += line # not stripped line because of indentation!
    g_stripped_file_cache[filename] = a
    return a

def precompile_hostcheck(hostname):
    if opt_verbose:
        sys.stderr.write("%s%s%-16s%s:" % (tty_bold, tty_blue, hostname, tty_normal))

    compiled_filename = precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    for fname in [ compiled_filename, source_filename ]:
        try:
            os.remove(fname)
        except:
            pass

    # check table, enriched with addition precompiled information.
    check_table = get_precompiled_check_table(hostname)
    if len(check_table) == 0:
        if opt_verbose:
            sys.stderr.write("(no Check_MK checks)\n")
        return

    output = file(source_filename + ".new", "w")
    output.write("#!/usr/bin/python\n")
    output.write("# encoding: utf-8\n")

    # Self-compile: replace symlink with precompiled python-code, if
    # we are run for the first time
    if delay_precompile:
        output.write("""
import os
if os.path.islink(%(dst)r):
    import py_compile
    os.remove(%(dst)r)
    py_compile.compile(%(src)r, %(dst)r, %(dst)r, True)
    os.chmod(%(dst)r, 0755)

""" % { "src" : source_filename, "dst" : compiled_filename })

    output.write(stripped_python_file(modules_dir + "/check_mk_base.py"))

    # TODO: can we avoid adding this module if no predictive monitoring
    # is being used?
    output.write(stripped_python_file(modules_dir + "/prediction.py"))

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v and -d are supported
opt_verbose = ('-v' in sys.argv) and 1 or 0
opt_debug   = '-d' in sys.argv

# make sure these names are defined (even if never needed)
no_discovery_possible = None
""")

    # Compile in all neccessary global variables
    output.write("\n# Global variables\n")
    for var in [ 'check_mk_version', 'tcp_connect_timeout', 'agent_min_version',
                 'perfdata_format', 'aggregation_output_format',
                 'aggr_summary_hostname', 'nagios_command_pipe_path',
                 'check_result_path', 'check_submission', 'monitoring_core',
                 'var_dir', 'counters_directory', 'tcp_cache_dir', 'tmp_dir', 'log_dir',
                 'snmpwalks_dir', 'check_mk_basedir', 'nagios_user', 'rrd_path', 'rrdcached_socket',
                 'omd_root',
                 'www_group', 'cluster_max_cachefile_age', 'check_max_cachefile_age',
                 'piggyback_max_cachefile_age',
                 'simulation_mode', 'agent_simulator', 'aggregate_check_mk',
                 'check_mk_perfdata_with_times', 'livestatus_unix_socket',
                 'use_inline_snmp', 'record_inline_snmp_stats',
                 ]:
        output.write("%s = %r\n" % (var, globals()[var]))

    output.write("\n# Checks for %s\n\n" % hostname)
    output.write("def get_sorted_check_table(hostname, remove_duplicates=False, world='config'):\n    return %r\n\n" % check_table)

    # Do we need to load the SNMP module? This is the case, if the host
    # has at least one SNMP based check. Also collect the needed check
    # types and sections.
    need_snmp_module = False
    needed_check_types = set([])
    needed_sections = set([])
    service_timeperiods = {}
    check_intervals = {}
    for check_type, item, param, descr, aggr in check_table:
        if check_type not in check_info:
            sys.stderr.write('Warning: Ignoring missing check %s.\n' % check_type)
            continue
        if check_info[check_type].get("extra_sections"):
            for section in check_info[check_type]["extra_sections"]:
                needed_check_types.add(section)
                needed_sections.add(section.split(".")[0])
        period = check_period_of(hostname, descr)
        if period:
            service_timeperiods[descr] = period
        interval = check_interval_of(hostname, check_type)
        if interval is not None:
            check_intervals[check_type] = interval

        needed_sections.add(check_type.split(".")[0])
        needed_check_types.add(check_type)
        if check_uses_snmp(check_type):
            need_snmp_module = True

    output.write("precompiled_check_intervals = %r\n" % check_intervals)
    output.write("def check_interval_of(hostname, checktype):\n    return precompiled_check_intervals.get(checktype)\n\n")
    output.write("precompiled_service_timeperiods = %r\n" % service_timeperiods)
    output.write("def check_period_of(hostname, service):\n    return precompiled_service_timeperiods.get(service)\n\n")

    if need_snmp_module:
        output.write(stripped_python_file(modules_dir + "/snmp.py"))

        if has_inline_snmp and use_inline_snmp:
            output.write(stripped_python_file(modules_dir + "/inline_snmp.py"))
            output.write("\ndef oid_range_limits_of(hostname):\n    return %r\n" % oid_range_limits_of(hostname))
        else:
            output.write("has_inline_snmp = False\n")
    else:
        output.write("has_inline_snmp = False\n")

    if agent_simulator:
        output.write(stripped_python_file(modules_dir + "/agent_simulator.py"))

    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table
    filenames = []
    for check_type in needed_check_types:
        basename = check_type.split(".")[0]
        # Add library files needed by check (also look in local)
        for lib in set(check_includes.get(basename, [])):
            if local_checks_dir and os.path.exists(local_checks_dir + "/" + lib):
                to_add = local_checks_dir + "/" + lib
            else:
                to_add = checks_dir + "/" + lib
            if to_add not in filenames:
                filenames.append(to_add)

        # Now add check file(s) itself
        paths = find_check_plugins(check_type)
        if not paths:
            raise MKGeneralException("Cannot find check file %s needed for check type %s" % \
                                     (basename, check_type))

        for path in paths:
            if path not in filenames:
                filenames.append(path)


    output.write("check_info = {}\n" +
                 "check_includes = {}\n" +
                 "precompile_params = {}\n" +
                 "factory_settings = {}\n" +
                 "checkgroup_of = {}\n" +
                 "check_config_variables = []\n" +
                 "check_default_levels = {}\n" +
                 "snmp_info = {}\n" +
                 "snmp_scan_functions = {}\n")

    for filename in filenames:
        output.write("# %s\n" % filename)
        output.write(stripped_python_file(filename))
        output.write("\n\n")
        if opt_verbose:
            sys.stderr.write(" %s%s%s" % (tty_green, filename.split('/')[-1], tty_normal))

    # Make sure all checks are converted to the new API
    output.write("convert_check_info()\n")

    # handling of clusters
    if is_cluster(hostname):
        output.write("clusters = { %r : %r }\n" %
                     (hostname, nodes_of(hostname)))
        output.write("def is_cluster(hostname):\n    return True\n\n")
    else:
        output.write("clusters = {}\ndef is_cluster(hostname):\n    return False\n\n")

    output.write("def clusters_of(hostname):\n    return %r\n\n" % clusters_of(hostname))

    # snmp hosts
    output.write("def is_snmp_host(hostname):\n   return %r\n\n" % is_snmp_host(hostname))
    output.write("def is_tcp_host(hostname):\n   return %r\n\n" % is_tcp_host(hostname))
    output.write("def is_usewalk_host(hostname):\n   return %r\n\n" % is_usewalk_host(hostname))
    if has_inline_snmp and use_inline_snmp:
        output.write("def is_snmpv2c_host(hostname):\n   return %r\n\n" % is_snmpv2c_host(hostname))
        output.write("def is_bulkwalk_host(hostname):\n   return %r\n\n" % is_bulkwalk_host(hostname))
        output.write("def snmp_timing_of(hostname):\n   return %r\n\n" % snmp_timing_of(hostname))
        output.write("def snmp_credentials_of(hostname):\n   return %s\n\n" % pprint.pformat(snmp_credentials_of(hostname)))
        output.write("def snmp_port_of(hostname):\n   return %r\n\n" % snmp_port_of(hostname))
    else:
        output.write("def snmp_port_spec(hostname):\n    return %r\n\n" % snmp_port_spec(hostname))
        output.write("def snmp_walk_command(hostname):\n   return %r\n\n" % snmp_walk_command(hostname))

    # IP addresses
    needed_ipaddresses = {}
    nodes = []
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            ipa = lookup_ipaddress(node)
            needed_ipaddresses[node] = ipa
            nodes.append( (node, ipa) )
        try:
            ipaddress = lookup_ipaddress(hostname) # might throw exception
            needed_ipaddresses[hostname] = ipaddress
        except:
            ipaddress = None
    else:
        ipaddress = lookup_ipaddress(hostname) # might throw exception
        needed_ipaddresses[hostname] = ipaddress
        nodes = [ (hostname, ipaddress) ]

    output.write("ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("def lookup_ipaddress(hostname):\n   return ipaddresses.get(hostname)\n\n");

    # datasource programs. Is this host relevant?
    # ACHTUNG: HIER GIBT ES BEI CLUSTERN EIN PROBLEM!! WIR MUESSEN DIE NODES
    # NEHMEN!!!!!

    dsprogs = {}
    for node, ipa in nodes:
        program = get_datasource_program(node, ipa)
        dsprogs[node] = program
    output.write("def get_datasource_program(hostname, ipaddress):\n" +
                 "    return %r[hostname]\n\n" % dsprogs)

    # aggregation
    output.write("def host_is_aggregated(hostname):\n    return %r\n\n" % host_is_aggregated(hostname))

    # TCP and SNMP port of agent
    output.write("def agent_port_of(hostname):\n    return %d\n\n" % agent_port_of(hostname))

    # Exit code of Check_MK in case of various errors
    output.write("def exit_code_spec(hostname):\n    return %r\n\n" % exit_code_spec(hostname))

    # Piggyback translations
    output.write("def get_piggyback_translation(hostname):\n    return %r\n\n" % get_piggyback_translation(hostname))

    # Expected agent version
    output.write("def agent_target_version(hostname):\n    return %r\n\n" % (agent_target_version(hostname),))

    # SNMP character encoding
    output.write("def get_snmp_character_encoding(hostname):\n    return %r\n\n"
      % get_snmp_character_encoding(hostname))

    # Parameters for checks: Default values are defined in checks/*. The
    # variables might be overridden by the user in main.mk. We need
    # to set the actual values of those variables here. Otherwise the users'
    # settings would get lost. But we only need to set those variables that
    # influence the check itself - not those needed during inventory.
    for var in check_config_variables:
        output.write("%s = %r\n" % (var, eval(var)))

    # The same for those checks that use the new API
    for check_type in needed_check_types:
        for var in check_info[check_type].get("check_config_variables", []):
            output.write("%s = %r\n" % (var, eval(var)))

    # perform actual check with a general exception handler
    output.write("try:\n")
    output.write("    sys.exit(do_check(%r, %r))\n" % (hostname, ipaddress))
    output.write("except SystemExit, e:\n")
    output.write("    sys.exit(e.code)\n")
    output.write("except Exception, e:\n")
    output.write("    import traceback, pprint\n")

    # status output message
    output.write("    sys.stdout.write(\"UNKNOWN - Exception in precompiled check: %s (details in long output)\\n\" % e)\n")

    # generate traceback for long output
    output.write("    sys.stdout.write(\"Traceback: %s\\n\" % traceback.format_exc())\n")

    # debug logging
    output.write("\n")
    output.write("    l = file(log_dir + \"/crashed-checks.log\", \"a\")\n")
    output.write("    l.write((\"Exception in precompiled check:\\n\"\n")
    output.write("            \"  Check_MK Version: %s\\n\"\n")
    output.write("            \"  Date:             %s\\n\"\n")
    output.write("            \"  Host:             %s\\n\"\n")
    output.write("            \"  %s\\n\") % (\n")
    output.write("            check_mk_version,\n")
    output.write("            time.strftime(\"%Y-%d-%m %H:%M:%S\"),\n")
    output.write("            \"%s\",\n" % hostname)
    output.write("            traceback.format_exc().replace('\\n', '\\n      ')))\n")
    output.write("    l.close()\n")

    output.write("    sys.exit(3)\n")
    output.close()

    # compile python (either now or delayed), but only if the source
    # code has not changed. The Python compilation is the most costly
    # operation here.
    if os.path.exists(source_filename):
        if file(source_filename).read() == file(source_filename + ".new").read():
            if opt_verbose:
                sys.stderr.write(" (%s is unchanged)\n" % source_filename)
            os.remove(source_filename + ".new")
            return
        elif opt_verbose:
            sys.stderr.write(" (new content)")

    os.rename(source_filename + ".new", source_filename)
    if not delay_precompile:
        py_compile.compile(source_filename, compiled_filename, compiled_filename, True)
        os.chmod(compiled_filename, 0755)
    else:
        if os.path.exists(compiled_filename) or os.path.islink(compiled_filename):
            os.remove(compiled_filename)
        os.symlink(hostname + ".py", compiled_filename)

    if opt_verbose:
        sys.stderr.write(" ==> %s.\n" % compiled_filename)

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

derived_config_variable_names = [ "hosttags" ]

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
    for varname in list(config_variable_names) + derived_config_variable_names:
        if varname not in skipped_config_variable_names:
            val = globals()[varname]
            if packable(varname, val):
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
    import termios,struct,fcntl
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
            sys.stderr.write('ERROR: Skipping invalid manpage: %s: %s\n' % (checkname, e))
            continue

        try:
            cat = parsed["catalog"]
        except KeyError:
            if opt_debug:
                raise
            sys.stderr.write('ERROR: Skipping invalid manpage: %s (Catalog info missing)\n' % checkname)
            continue

        if not cat:
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
    execfile(modules_dir + "/catalog.py", globals())
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

    if "agents" not in parsed:
        raise Exception("Section agents missing in man page of %s\n" % (checkname))
    else:
        parsed["agents"] = parsed["agents"].replace(" ","").split(",")

    if parsed.get("catalog"):
        parsed["catalog"] = parsed["catalog"].split("/")

    return parsed


def show_check_manual(checkname):
    filename = all_manuals().get(checkname)

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

    if not filename:
        sys.stdout.write("No manpage for %s. Sorry.\n" % checkname)
        return

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
        header = {}
        for key, value in sections['header']:
            header[key] = value.strip()

        print_sectionheader(checkname, header['title'])
        if opt_nowiki:
            sys.stderr.write("<tr><td class=tt>%s</td><td>[check_%s|%s]</td></tr>\n" % (checkname, checkname, header['title']))
        ags = []
        for agent in header['agents'].split(","):
            agent = agent.strip()
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
        print "Invalid check manpage %s: missing %s" % (filename, e)


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
    def __init__(self, content):
        self.content = content
        self.pointer = 0

    def size(self):
        return len(self.content)

    def read(self, size):
        new_end = self.pointer + size
        data = self.content[self.pointer:new_end]
        self.pointer = new_end
        return data

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
    if len(hosts) == 0:
        hosts = all_active_hosts() + all_active_clusters()
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
    for hn in all_active_hosts() + all_active_clusters():
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
    for h in all_active_hosts() + all_active_clusters():
        if hosttags_match_taglist(tags_of_host(h), tags):
            hosts.append(h)
    return hosts


# Implementation of option -d
def output_plain_hostinfo(hostname):
    info = read_cache_file(hostname, 999999999)
    if info:
        sys.stdout.write(info)
        return
    if is_tcp_host(hostname):
        try:
            ipaddress = lookup_ipaddress(hostname)
            sys.stdout.write(get_agent_info(hostname, ipaddress, 0))
        except MKAgentError, e:
            sys.stderr.write("Problem contacting agent: %s\n" % (e,))
            sys.exit(3)
        except MKGeneralException, e:
            sys.stderr.write("General problem: %s\n" % (e,))
            sys.exit(3)
        except socket.gaierror, e:
            sys.stderr.write("Network error: %s\n" % e)
        except Exception, e:
            sys.stderr.write("Unexpected exception: %s\n" % (e,))
            sys.exit(3)

    sys.stdout.write(get_piggyback_info(hostname))

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

def do_snmpwalk_on(hostname, filename):
    verbose("%s:\n" % hostname)
    ip = lookup_ipaddress(hostname)

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

            results = snmpwalk_on_suboid(hostname, ip, oid, hex_plain = True)
            for oid, value in results:
                out.write("%s %s\n" % (oid, value))
            verbose("%d variables.\n" % len(results))
        except:
            if opt_debug:
                raise

    out.close()
    verbose("Successfully Wrote %s%s%s.\n" % (tty_bold, filename, tty_normal))

def do_snmpget(oid, hostnames):
    if len(hostnames) == 0:
        for host in all_active_hosts():
            if is_snmp_host(host):
                hostnames.append(host)

    for host in hostnames:
        ip = lookup_ipaddress(host)
        value = get_single_oid(host, ip, oid)
        sys.stdout.write("%s (%s): %r\n" % (host, ip, value))


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
        hostlist = all_hosts_untagged + all_active_clusters()
    hostlist.sort()
    for hostname in hostlist:
        dump_host(hostname)

def dump_host(hostname):
    print
    if is_cluster(hostname):
        color = tty_bgmagenta
        add_txt = " (cluster of " + (",".join(nodes_of(hostname))) + ")"
        try:
            ipaddress = lookup_ipaddress(hostname)
        except:
            ipaddress = "0.0.0.0"
    else:
        color = tty_bgblue
        try:
            ipaddress = lookup_ipaddress(hostname)
            add_txt = " (%s)" % ipaddress
        except:
            add_txt = " (no DNS, no entry in ipaddresses)"
            ipaddress = "X.X.X.X"
    print "%s%s%s%-78s %s" % (color, tty_bold, tty_white, hostname + add_txt, tty_normal)

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
            if has_inline_snmp and use_inline_snmp:
                inline = "yes"
            else:
                inline = "no"

            credentials = snmp_credentials_of(hostname)
            if type(credentials) in [ str, unicode ]:
                cred = "community: \'%s\'" % credentials
            else:
                cred = "credentials: '%s'" % ", ".join(credentials)

            if is_bulkwalk_host(hostname):
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
        item,
        params,
        description,
        make_utf8(",".join(service_extra_conf(hostname, description, service_groups))),
        if_aggr(aggregated_service_name(hostname, description)),
        if_aggr(",".join(service_extra_conf(hostname, aggregated_service_name(hostname, description), summary_service_groups))),
        ",".join(deps)
        ]
                  for checktype, item, params, description, deps in check_items ], "  ")

def print_table(headers, colors, rows, indent = ""):
    lengths = [ len(h) for h in headers ]
    for row in rows:
        lengths = [ max(len(str(c)), l) for c, l in zip(row, lengths) ]
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
 cmk --create-rrd [--keepalive|SPEC]  create round robin database (only CMC)
 cmk --convert-rrds [--split] [H...]  convert exiting RRD to new format (only CMC)
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
  --keepalive    used by Check_MK Mirco Core: run check and --notify in continous
                 mode. Read data from stdin and von from cmd line and environment
  --cmc-file=X   relative filename for CMC config file (used by -B/-U)
  --extraoid A   Do --snmpwalk also on this OID, in addition to mib-2 and enterprises.
                 You can specify this option multiple times.
  --oid A        Do --snmpwalk on this OID instead of mib-2 and enterprises.
                 You can specify this option multiple times.
  --hw-changes=S --inventory-as-check: Use monitoring state S for HW changes
  --sw-changes=S --inventory-as-check: Use monitoring state S for SW changes

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
  checks if an inventory would find new services for the host.

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
    if monitoring_core == "cmc":
        do_create_cmc_config(opt_cmc_relfilename, False) # do not use rushed ahead config
    else:
        out = file(nagios_objects_file, "w")
        create_nagios_config(out)
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


def do_output_nagios_conf(args):
    if len(args) == 0:
        args = None
    create_nagios_config(sys.stdout, args)

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

        if not lock_objects_file():
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
            sys.stderr.write("Nagios configuration is invalid. Rolling back.\n")
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
def lock_objects_file():
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
            return False
    return True


def do_donation():
    donate = []
    cache_files = os.listdir(tcp_cache_dir)
    for host in all_hosts_untagged:
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
        hosts = filter(lambda h: in_binary_hostlist(h, scanparent_hosts), all_hosts_untagged)

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
    return 0 == os.system("ping -q -i 0.2 -l 3 -c %d -W 5 '%s' >/dev/null 2>&1" %
      (probes, ip)) >> 8

def scan_parents_of(hosts, silent=False, settings={}):
    if monitoring_host:
        nagios_ip = lookup_ipaddress(monitoring_host)
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
            ip = lookup_ipaddress(host)
            command = "traceroute -w %d -q %d -m %d -n '%s' 2>&1" % (
                settings.get("timeout", 8),
                settings.get("probes", 2),
                settings.get("max_ttl", 10),
                ip)
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
        for host in all_hosts_untagged:
            try:
                ip_to_hostname_cache[lookup_ipaddress(host)] = host
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
    global g_counters
    g_counters = {}
    global g_infocache
    g_infocache = {}
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

    if has_inline_snmp and use_inline_snmp:
        cleanup_inline_snmp_globals()


# Diagnostic function for detecting global variables that have
# changed during checking. This is slow and canno be used
# in production mode.
def copy_globals():
    import copy
    global_saved = {}
    for varname, value in globals().items():
        # Some global caches are allowed to change.
        if varname not in [ "g_service_description", "g_multihost_checks",
                            "g_check_table_cache", "g_singlehost_checks",
                            "g_nodesof_cache", "g_compiled_regexes", "vars_before_config",
                            "g_initial_times", "g_keepalive_initial_memusage",
                            "g_dns_cache", "g_ip_lookup_cache", "g_converted_rulesets_cache" ] \
            and type(value).__name__ not in [ "function", "module", "SRE_Pattern" ]:
            global_saved[varname] = copy.copy(value)
    return global_saved


# Determine currently (VmSize, VmRSS) in Bytes
def current_memory_usage():
    parts = file('/proc/self/stat').read().split()
    vsize = int(parts[22])        # in Bytes
    rss   = int(parts[23]) * 4096 # in Pages
    return (vsize, rss)

keepalive_memcheck_cycle = 20
g_keepalive_initial_memusage = None
def keepalive_check_memory(num_checks, keepalive_fd):
    if num_checks % keepalive_memcheck_cycle != 0: # Only do this after every 10 checks
        return

    global g_keepalive_initial_memusage
    if not g_keepalive_initial_memusage:
        g_keepalive_initial_memusage = current_memory_usage()
    else:
        usage = current_memory_usage()
        # Allow VM size to grow by at most 50%
        if usage[0] > 1.5 * g_keepalive_initial_memusage[0]:
            sys.stderr.write("memory usage increased from %s to %s after %d check cycles. Restarting.\n" % (
                    get_bytes_human_readable(g_keepalive_initial_memusage[0]),
                    get_bytes_human_readable(usage[0]), num_checks))
            restart_myself(keepalive_fd)


def restart_myself(keepalive_fd):
    sys.argv = [ x for x in sys.argv if not x.startswith('--keepalive-fd=') ]
    os.execvp("cmk", sys.argv + [ "--keepalive-fd=%d" % keepalive_fd ])


def do_check_keepalive():
    global g_initial_times, g_timeout, check_max_cachefile_age, inventory_max_cachefile_age

    def check_timeout(signum, frame):
        raise MKCheckTimeout()

    signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc

    # Prevent against plugins that output debug information (but shouldn't).
    # Their stdout will interfer with communication with the Micro Core.
    # So we simply redirect stdout to stderr, which will appear in the cmc.log,
    # with the following trick:
    # 1. move the filedescriptor 1 to a parking position
    # 2. dup the stderr channel to stdout (2 to 1)
    # 3. Send our answers to the Micro Core with the parked FD.
    # BEWARE: this must not happen after we have execve'd ourselves!
    if opt_keepalive_fd:
        keepalive_fd = opt_keepalive_fd
    else:
        keepalive_fd = os.dup(1)
        os.dup2(2, 1)  # Send stuff that is written to stdout instead to stderr

    num_checks = 0 # count total number of check cycles

    read_packed_config()
    global vars_before_config
    vars_before_config = set([])

    orig_check_max_cachefile_age     = check_max_cachefile_age
    orig_inventory_max_cachefile_age = inventory_max_cachefile_age

    global total_check_output
    total_check_output = ""
    if opt_debug:
        before = copy_globals()

    ipaddress_cache = {}

    while True:
        cleanup_globals()
        cmdline = keepalive_read_line()
        g_initial_times = os.times()

        cmdline = cmdline.strip()
        if cmdline == "*":
            read_packed_config()
            cleanup_globals()
            reset_global_caches()
            before = copy_globals()
            continue

        elif not cmdline:
            break

        # Always cleanup the total check output var before handling a new task
        total_check_output = ""

        num_checks += 1

        g_timeout = int(keepalive_read_line())
        try: # catch non-timeout exceptions
            try: # catch timeouts
                signal.signal(signal.SIGALRM, check_timeout)
                signal.alarm(g_timeout)

                # The CMC always provides arguments. This is the only used case for CMC. The last
                # two arguments are the hostname and the ipaddress of the host to be asked for.
                # The other arguments might be different parameters to configure the actions to
                # be done
                args = cmdline.split()
                if '--cache' in args:
                    args.remove('--cache')
                    check_max_cachefile_age     = 1000000000
                    inventory_max_cachefile_age = 1000000000
                else:
                    check_max_cachefile_age     = orig_check_max_cachefile_age
                    inventory_max_cachefile_age = orig_inventory_max_cachefile_age

                # FIXME: remove obsolete check-inventory
                if '--check-inventory' in args:
                    args.remove('--check-inventory')
                    mode_function = check_discovery
                elif '--check-discovery' in args:
                    args.remove('--check-discovery')
                    mode_function = check_discovery
                else:
                    mode_function = do_check

                if len(args) >= 2:
                    hostname, ipaddress = args[:2]
                else:
                    hostname = args[0]
                    ipaddress = None

                if ipaddress == None:
                    if hostname in ipaddress_cache:
                        ipaddress = ipaddress_cache[hostname]
                    else:
                        if is_cluster(hostname):
                            ipaddress = None
                        else:
                            try:
                                ipaddress = lookup_ipaddress(hostname)
                            except:
                                raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)
                        ipaddress_cache[hostname] = ipaddress

                status = mode_function(hostname, ipaddress)
                signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc
                signal.alarm(0)

            except MKCheckTimeout:
                signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc
                spec = exit_code_spec(hostname)
                status = spec.get("timeout", 2)
                total_check_output = "%s - Check_MK timed out after %d seconds\n" % (
                    core_state_names[status], g_timeout)

            os.write(keepalive_fd, "%03d\n%08d\n%s" %
                 (status, len(total_check_output), total_check_output))
            total_check_output = ""

        except Exception, e:
            signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc
            signal.alarm(0)
            if opt_debug:
                raise
            output = "UNKNOWN - %s\n" % e
            os.write(keepalive_fd, "%03d\n%08d\n%s" % (3, len(output), output))

        # Flush file descriptors of stdout and stderr, so that diagnostic
        # messages arrive in time in cmc.log
        sys.stdout.flush()
        sys.stderr.flush()

        cleanup_globals() # Prepare for next check

        # Check if all global variables are clean, but only in debug mode
        if opt_debug:
            after = copy_globals()
            for varname, value in before.items():
                if value != after[varname]:
                    sys.stderr.write("WARNING: global variable %s has changed: %r ==> %s\n"
                           % (varname, value, repr(after[varname])[:50]))
            new_vars = set(after.keys()).difference(set(before.keys()))
            if (new_vars):
                sys.stderr.write("WARNING: new variable appeared: %s\n" % ", ".join(new_vars))
            sys.stderr.flush()

        keepalive_check_memory(num_checks, keepalive_fd)
        # In case of profiling do just this one cycle and end afterwards
        if g_profile:
            output_profile()
            sys.exit(0)

        # end of while True:...


# Just one lines from stdin. But: make sure that
# nothing more is read - not even into some internal
# buffer of sys.stdin! We do this by reading every
# single byte. I know that this is not performant,
# but we just read hostnames - not much data.

def keepalive_read_line():
    line = ""
    while True:
        byte = os.read(0, 1)
        if byte == '\n':
            return line
        elif not byte: # EOF
            return ''
        else:
            line += byte


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

def read_config_files(with_autochecks=True, with_conf_d=True):
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

    # Strip off host tags from the list of all_hosts.  Host tags can be
    # appended to the hostnames in all_hosts, separated by pipe symbols,
    # e.g. "zbghlnx04|bgh|linux|test" and are stored in a separate
    # dictionary called 'hosttags'
    global hosttags, all_hosts_untagged
    hosttags = {}
    for taggedhost in all_hosts + clusters.keys():
        parts = taggedhost.split("|")
        hosttags[parts[0]] = parts[1:]
    all_hosts_untagged = all_active_hosts()

    # Sanity check for duplicate hostnames
    seen_hostnames = set([])
    for hostname in strip_tags(all_hosts + clusters.keys()):
        if hostname in seen_hostnames:
            sys.stderr.write("Error in configuration: duplicate host '%s'\n" % hostname)
            sys.exit(3)
        seen_hostnames.add(hostname)

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
                             'all_hosts_untagged' ,'taggedhost' ,'hostname'])
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

    descr = service_description(checktype, item)

    # Get parameters configured via checkgroup_parameters
    entries = get_checkgroup_parameters(host, checktype, item)

    # Get parameters configured via check_parameters
    entries += service_extra_conf(host, descr, check_parameters)

    if len(entries) > 0:
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

    if item == None: # checks without an item
        return host_extra_conf(host, rules)
    else: # checks with an item need service-specific rules
        return service_extra_conf(host, str(item), rules)


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

load_checks()

opt_nowiki     = False
opt_split_rrds = False

# Do option parsing and execute main function -
short_options = 'ASHVLCURODMmd:Ic:nhvpXPNBilf'
long_options = [ "help", "version", "verbose", "compile", "debug", "interactive",
                 "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
                 "flush", "package", "localize", "donate", "snmpwalk", "oid=", "extraoid=",
                 "snmptranslate", "bake-agents", "force", "show-snmp-stats",
                 "usewalk", "scan-parents", "procs=", "automation=", "notify",
                 "snmpget=", "profile", "keepalive", "keepalive-fd=", "create-rrd",
                 "convert-rrds", "split-rrds",
                 "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                 "man", "nowiki", "config-check", "backup=", "restore=",
                 "check-inventory=", "check-discovery=", "paths",
                 "checks=", "inventory", "inventory-as-check=", "hw-changes=", "sw-changes=",
                 "cmc-file=", "browse-man", "list-man", "update-dns-cache", "cap" ]

non_config_options = ['-L', '--list-checks', '-P', '--package', '-M', '--notify',
                      '--man', '-V', '--version' ,'-h', '--help', '--automation',
                      '--create-rrd', '--convert-rrds', '--keepalive', '--cap' ]

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
        opt_use_cachefile = True
        check_max_cachefile_age     = 1000000000
        inventory_max_cachefile_age = 1000000000
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
    elif o == "--hw-changes":
        opt_inv_hw_changes = int(a)
    elif o == "--sw-changes":
        opt_inv_sw_changes = int(a)

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
            do_output_nagios_conf(args)
            done = True
        elif o == '-B':
            do_update(with_precompile=False)
            done = True
        elif o in [ '-C', '--compile' ]:
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
            execfile(modules_dir + "/packaging.py")
            do_packaging(args)
            done = True
        elif o in ['--localize']:
            execfile(modules_dir + "/localize.py")
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
        elif o == '--scan-parents':
            do_scan_parents(args)
            done = True
        elif o == '--automation':
            execfile(modules_dir + "/automation.py")
            do_automation(a, args)
            done = True
        elif o in [ '-i', '--inventory' ]:
            execfile(modules_dir + "/inventory.py")
            if args:
                hostnames = parse_hostname_list(args, with_clusters = False)
            else:
                hostnames = None
            do_inv(hostnames)
            done = True
        elif o == '--inventory-as-check':
            execfile(modules_dir + "/inventory.py")
            do_inv_check(a)
            done = True
        elif o == '--notify':
            read_config_files(False, True)
            sys.exit(do_notify(args))
        elif o == '--create-rrd':
            read_config_files(False, True)
            execfile(modules_dir + "/rrd.py")
            do_create_rrd(args)
            done = True
        elif o == '--convert-rrds':
            read_config_files(False, True)
            execfile(modules_dir + "/rrd.py")
            do_convert_rrds(args)
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
        do_discovery(hostnames, check_types, seen_I == 1)
        done = True

    if not done:
        if (len(args) == 0 and not opt_keepalive) or len(args) > 2:
            usage()
            sys.exit(1)

        # handle --keepalive
        elif opt_keepalive:
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
                        ipaddress = lookup_ipaddress(hostname)
                    except:
                        print "Cannot resolve hostname '%s'." % hostname
                        sys.exit(2)

            exit_status = do_check(hostname, ipaddress, check_types)

    output_profile()
    sys.exit(exit_status)

except (MKGeneralException, MKBailOut), e:
    sys.stderr.write("%s\n" % e)
    if opt_debug:
        raise
    sys.exit(3)

