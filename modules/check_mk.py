#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# These variable will be substituted at 'make dist' time
check_mk_version  = '(inofficial)'

# Some things have to be done before option parsing and might
# want to output some verbose messages.
g_profile      = None
g_profile_path = 'profile.out'

if __name__ == "__main__":
    opt_debug        = '--debug' in sys.argv[1:]
    opt_verbose      = '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]
    if '--profile' in sys.argv[1:]:
        import cProfile
        g_profile = cProfile.Profile()
        g_profile.enable()
        if opt_verbose:
            sys.stderr.write("Enabled profiling.\n")

else:
    opt_verbose = False
    opt_debug = False

# are we running OMD? If yes, honor local/ hierarchy
omd_root = os.getenv("OMD_ROOT", None)
if omd_root:
    local_share              = omd_root + "/local/share/check_mk"
    local_checks_dir         = local_share + "/checks"
    local_notifications_dir  = local_share + "/notifications"
    local_check_manpages_dir = local_share + "/checkman"
    local_agents_dir         = local_share + "/agents"
    local_mibs_dir           = local_share + "/mibs"
    local_web_dir            = local_share + "/web"
    local_pnp_templates_dir  = local_share + "/pnp-templates"
    local_doc_dir            = omd_root + "/local/share/doc/check_mk"
    local_locale_dir         = local_share + "/locale"
else:
    local_checks_dir         = None
    local_notifications_dir  = None
    local_check_manpages_dir = None
    local_agents_dir         = None
    local_mibs_dir           = None
    local_web_dir            = None
    local_pnp_templates_dir  = None
    local_doc_dir            = None
    local_locale_dir         = None

#   +----------------------------------------------------------------------+
#   |        ____       _   _                                              |
#   |       |  _ \ __ _| |_| |__  _ __   __ _ _ __ ___   ___  ___          |
#   |       | |_) / _` | __| '_ \| '_ \ / _` | '_ ` _ \ / _ \/ __|         |
#   |       |  __/ (_| | |_| | | | | | | (_| | | | | | |  __/\__ \         |
#   |       |_|   \__,_|\__|_| |_|_| |_|\__,_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Pathnames, directories   and  other  settings.  All  these  settings
# should be  overriden by  /usr/share/check_mk/modules/defaults, which
# is created by setup.sh. The user might override those values again
# in main.mk

default_config_dir                 = '/etc/check_mk'
check_mk_configdir                 = default_config_dir + "/conf.d"
checks_dir                         = '/usr/share/check_mk/checks'
notifications_dir                  = '/usr/share/check_mk/notifications'
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

def verbose(t):
    if opt_verbose:
        sys.stderr.write(t)
        sys.stderr.flush()


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
elif __name__ == "__main__":
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


if __name__ == "__main__":
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

else:
    check_mk_basedir = default_config_dir
    check_mk_configfile = default_config_dir + "/main.mk"


#   +----------------------------------------------------------------------+
#   |        ____       _     ____        __             _ _               |
#   |       / ___|  ___| |_  |  _ \  ___ / _| __ _ _   _| | |_ ___         |
#   |       \___ \ / _ \ __| | | | |/ _ \ |_ / _` | | | | | __/ __|        |
#   |        ___) |  __/ |_  | |_| |  __/  _| (_| | |_| | | |_\__ \        |
#   |       |____/ \___|\__| |____/ \___|_|  \__,_|\__,_|_|\__|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Before we read the configuration files we create default settings
# for all variables. The user can easily override them.

# define magic keys for use in host extraconf lists
PHYSICAL_HOSTS = [ '@physical' ] # all hosts but not clusters
CLUSTER_HOSTS  = [ '@cluster' ]  # all cluster hosts
ALL_HOSTS      = [ '@all' ]      # physical and cluster hosts
ALL_SERVICES   = [ "" ]          # optical replacement"
NEGATE         = '@negate'       # negation in boolean lists

# Basic Settings
monitoring_core                    = "nagios" # other option: "cmc"
agent_port                         = 6556
agent_ports                        = []
snmp_ports                         = [] # UDP ports used for SNMP
tcp_connect_timeout                = 5.0
use_dns_cache                      = True # prevent DNS by using own cache file
delay_precompile                   = False  # delay Python compilation to Nagios execution
restart_locking                    = "abort" # also possible: "wait", None
check_submission                   = "file" # alternative: "pipe"
aggr_summary_hostname              = "%s-s"
agent_min_version                  = 0 # warn, if plugin has not at least version
check_max_cachefile_age            = 0 # per default do not use cache files when checking
cluster_max_cachefile_age          = 90   # secs.
piggyback_max_cachefile_age        = 3600  # secs
piggyback_translation              = [] # Ruleset for translating piggyback host names
simulation_mode                    = False
agent_simulator                    = False
perfdata_format                    = "pnp" # also possible: "standard"
check_mk_perfdata_with_times       = True
debug_log                          = None
monitoring_host                    = None # deprecated
max_num_processes                  = 50

# SNMP communities and encoding
has_inline_snmp                    = False # is set to True by inline_snmp module, when available
use_inline_snmp                    = False
snmp_default_community             = 'public'
snmp_communities                   = []
snmp_timing                        = []
snmp_character_encodings           = []
explicit_snmp_communities          = {} # override the rule based configuration

# Inventory and inventory checks
inventory_check_interval           = None # Nagios intervals (4h = 240)
inventory_check_severity           = 1    # warning
inventory_max_cachefile_age        = 120  # secs.
always_cleanup_autochecks          = True

# Nagios templates and other settings concerning generation
# of Nagios configuration files. No need to change these values.
# Better adopt the content of the templates
host_template                      = 'check_mk_host'
cluster_template                   = 'check_mk_cluster'
pingonly_template                  = 'check_mk_pingonly'
active_service_template            = 'check_mk_active'
inventory_check_template           = 'check_mk_inventory'
passive_service_template           = 'check_mk_passive'
passive_service_template_perf      = 'check_mk_passive_perf'
summary_service_template           = 'check_mk_summarized'
service_dependency_template        = 'check_mk'
default_host_group                 = 'check_mk'
generate_hostconf                  = True
generate_dummy_commands            = True
dummy_check_commandline            = 'echo "ERROR - you did an active check on this service - please disable active checks" && exit 1'
nagios_illegal_chars               = '`;~!$%^&*|\'"<>?,()='

# Data to be defined in main.mk
checks                               = []
static_checks                        = {}
check_parameters                     = []
checkgroup_parameters                = {}
legacy_checks                        = [] # non-WATO variant of legacy checks
active_checks                        = {} # WATO variant for fully formalized checks
special_agents                       = {} # WATO variant for datasource_programs
custom_checks                        = [] # WATO variant for free-form custom checks without formalization
all_hosts                            = []
host_paths                           = {}
snmp_hosts                           = [ (['snmp'], ALL_HOSTS) ]
tcp_hosts                            = [ (['tcp'], ALL_HOSTS), (NEGATE, ['snmp'], ALL_HOSTS), (['!ping'], ALL_HOSTS) ]
bulkwalk_hosts                       = []
snmpv2c_hosts                        = []
snmp_without_sys_descr               = []
usewalk_hosts                        = []
dyndns_hosts                         = [] # use host name as ip address for these hosts
ignored_checktypes                   = [] # exclude from inventory
ignored_services                     = [] # exclude from inventory
ignored_checks                       = [] # exclude from inventory
host_groups                          = []
service_groups                       = []
service_contactgroups                = []
service_notification_periods         = [] # deprecated, will be removed soon.
host_notification_periods            = [] # deprecated, will be removed soon.
host_contactgroups                   = []
parents                              = []
define_hostgroups                    = None
define_servicegroups                 = None
define_contactgroups                 = None
contactgroup_members                 = {}
contacts                             = {}
timeperiods                          = {} # needed for WATO
clusters                             = {}
clustered_services                   = []
clustered_services_of                = {} # new in 1.1.4
datasource_programs                  = []
service_aggregations                 = []
service_dependencies                 = []
non_aggregated_hosts                 = []
aggregate_check_mk                   = False
aggregation_output_format            = "multiline" # new in 1.1.6. Possible also: "multiline"
summary_host_groups                  = []
summary_service_groups               = [] # service groups for aggregated services
summary_service_contactgroups        = [] # service contact groups for aggregated services
summary_host_notification_periods    = []
summary_service_notification_periods = []
ipaddresses                          = {} # mapping from hostname to ipaddress
only_hosts                           = None
distributed_wato_site                = None # used by distributed WATO
extra_host_conf                      = {}
extra_summary_host_conf              = {}
extra_service_conf                   = {}
extra_summary_service_conf           = {}
extra_nagios_conf                    = ""
service_descriptions                 = {}
donation_hosts                       = []
donation_command                     = 'mail -r checkmk@yoursite.de  -s "Host donation %s" donatehosts@mathias-kettner.de' % check_mk_version
scanparent_hosts                     = [ ( ALL_HOSTS ) ]
host_attributes                      = {} # needed by WATO, ignored by Check_MK
ping_levels                          = [] # special parameters for host/PING check_command
host_check_commands                  = [] # alternative host check instead of check_icmp
check_mk_exit_status                 = [] # Rule for specifying CMK's exit status in case of various errors
check_periods                        = []
snmp_check_interval                  = []


# global variables used to cache temporary values (not needed in check_mk_base)
ip_to_hostname_cache = None
# in memory cache, contains permanently cached ipaddresses from ipaddresses.cache during runtime
g_ip_lookup_cache = None

# The following data structures will be filled by the various checks
# found in the checks/ directory.
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


# Now include the other modules. They contain everything that is needed
# at check time (and many of what is also needed at administration time).
try:
    modules =  [ 'check_mk_base', 'snmp', 'notify', 'prediction', 'cmc', 'inline_snmp' ]
    for module in modules:
        filename = modules_dir + "/" + module + ".py"
        if os.path.exists(filename):
            execfile(filename)

except Exception, e:
    sys.stderr.write("Cannot read file %s: %s\n" % (filename, e))
    sys.exit(5)


#   +----------------------------------------------------------------------+
#   |     ____ _               _      _          _                         |
#   |    / ___| |__   ___  ___| | __ | |__   ___| |_ __   ___ _ __ ___     |
#   |   | |   | '_ \ / _ \/ __| |/ / | '_ \ / _ \ | '_ \ / _ \ '__/ __|    |
#   |   | |___| | | |  __/ (__|   <  | | | |  __/ | |_) |  __/ |  \__ \    |
#   |    \____|_| |_|\___|\___|_|\_\ |_| |_|\___|_| .__/ \___|_|  |___/    |
#   |                                             |_|                      |
#   |                                                                      |
#   | These functions are used by some checks at administration time.      |
#   +----------------------------------------------------------------------+

# The function no_inventory_possible is as stub function used for
# those checks that do not support inventory. It must be known before
# we read in all the checks
def no_inventory_possible(checkname, info):
    sys.stderr.write("Sorry. No inventory possible for check type %s.\n" % checkname)
    sys.exit(3)


#   +----------------------------------------------------------------------+
#   |       _                    _        _               _                |
#   |      | |    ___   __ _  __| |   ___| |__   ___  ___| | _____         |
#   |      | |   / _ \ / _` |/ _` |  / __| '_ \ / _ \/ __| |/ / __|        |
#   |      | |__| (_) | (_| | (_| | | (__| | | |  __/ (__|   <\__ \        |
#   |      |_____\___/ \__,_|\__,_|  \___|_| |_|\___|\___|_|\_\___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values. The user can override those variables in his configuration.
# Do not read in the checks if check_mk is called as module

if __name__ == "__main__":
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

    for f in filelist:
        if not f.endswith("~"): # ignore emacs-like backup files
            try:
                execfile(f)
            except Exception, e:
                sys.stderr.write("Error in plugin file %s: %s\n" % (f, e))
                if opt_debug:
                    raise
                sys.exit(5)

    # Now convert check_info to new format.
    convert_check_info()



#   +----------------------------------------------------------------------+
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def output_check_info():
    print "Available check types:"
    print
    print "                      plugin   perf-  in- "
    print "Name                  type     data   vent.  service description"
    print "-------------------------------------------------------------------------"

    checks_sorted = check_info.items()
    checks_sorted.sort()
    for check_type, check in checks_sorted:
        try:
            if check.get("has_perfdata", False):
                p = tty_green + tty_bold + "yes" + tty_normal
            else:
                p = "no"
            if check["inventory_function"] == None:
                i = "no"
            else:
                i = tty_blue + tty_bold + "yes" + tty_normal

            if check_uses_snmp(check_type):
                typename = tty_magenta + "snmp" + tty_normal
            else:
                typename = tty_yellow + "tcp " + tty_normal

            print (tty_bold + "%-19s" + tty_normal + "   %s     %-3s    %-3s    %s") % \
                  (check_type, typename, p, i, check["service_description"])
        except Exception, e:
            sys.stderr.write("ERROR in check_type %s: %s\n" % (check_type, e))



#   +----------------------------------------------------------------------+
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+

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

#   +----------------------------------------------------------------------+
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   +----------------------------------------------------------------------+

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

#   +----------------------------------------------------------------------+
#   |                      ____  _   _ __  __ ____                         |
#   |                     / ___|| \ | |  \/  |  _ \                        |
#   |                     \___ \|  \| | |\/| | |_) |                       |
#   |                      ___) | |\  | |  | |  __/                        |
#   |                     |____/|_| \_|_|  |_|_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+

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

def check_uses_snmp(check_type):
    return snmp_info.get(check_type.split(".")[0]) != None

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

def inline_snmp_get_oid(hostname, oid):
    s = init_snmp_host(hostname)

    if oid[-2:] == ".*":
        oid_prefix = oid[:-2]
        func       = s.getnext
        what       = 'GETNEXT'
    else:
        oid_prefix = oid
        func       = s.get
        what       = 'GET'

    if opt_debug:
        sys.stdout.write("Executing SNMP %s of %s on %s\n" % (what, oid_prefix, hostname))

    var_list = netsnmp.VarList(netsnmp.Varbind(oid))
    res = s.get(var_list)

    for var in var_list:
        value = var.val

        if what == "GETNEXT" and not var.tag.startswith(oid_prefix + "."):
            # In case of .*, check if prefix is the one we are looking for
            value = None

        elif value == 'NULL' or var.type in [ 'NOSUCHINSTANCE', 'NOSUCHOBJECT' ]:
            value = None

        elif value is not None:
            value = strip_snmp_value(value)

        if opt_verbose and opt_debug:
            sys.stdout.write("=> [%r] %s\n" % (value, var.type))

        return value

#   .--Classic SNMP--------------------------------------------------------.
#   |        ____ _               _        ____  _   _ __  __ ____         |
#   |       / ___| | __ _ ___ ___(_) ___  / ___|| \ | |  \/  |  _ \        |
#   |      | |   | |/ _` / __/ __| |/ __| \___ \|  \| | |\/| | |_) |       |
#   |      | |___| | (_| \__ \__ \ | (__   ___) | |\  | |  | |  __/        |
#   |       \____|_|\__,_|___/___/_|\___| |____/|_| \_|_|  |_|_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Non-inline SNMP handling code. Kept for compatibility.               |
#   '----------------------------------------------------------------------'


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
    if type(credentials) == str:
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
        options += " -t %d" % settings["timeout"]
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
              " -On -OQ -Oe -Ot %s%s %s 2>/dev/null" % (ipaddress, portspec, oid_prefix)

    if opt_debug:
        sys.stdout.write("Running '%s'\n" % command)

    snmp_process = os.popen(command, "r")
    line = snmp_process.readline().strip()
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

def snmp_scan(hostname, ipaddress):
    # Make hostname globally available for scan functions.
    # This is rarely used, but e.g. the scan for if/if64 needs
    # this to evaluate if_disabled_if64_checks.
    global g_hostname
    g_hostname = hostname

    if opt_verbose:
        sys.stdout.write("Scanning host %s(%s) for SNMP checks..." % (hostname, ipaddress))
    if not in_binary_hostlist(hostname, snmp_without_sys_descr):
        sys_descr = get_single_oid(hostname, ipaddress, ".1.3.6.1.2.1.1.1.0")
        if sys_descr == None:
            if opt_debug:
                sys.stderr.write("no SNMP answer\n")
            return []

    found = []
    for check_type, check in check_info.items():
        if check_type in ignored_checktypes:
            continue
        elif not check_uses_snmp(check_type):
            continue
        basename = check_type.split(".")[0]
        # The scan function should be assigned to the basename, because
        # subchecks sharing the same SNMP info of course should have
        # an identical scan function. But some checks do not do this
        # correctly
        scan_function = snmp_scan_functions.get(check_type,
                snmp_scan_functions.get(basename))
        if scan_function:
            try:
                result = scan_function(lambda oid: get_single_oid(hostname, ipaddress, oid))
                if result is not None and type(result) not in [ str, bool ]:
                    if opt_debug:
                        sys.stderr.write("[%s] Scan function returns invalid type (%s).\n" %
                                                                (check_type, type(result)))
                elif result:
                    found.append(check_type)
                    if opt_verbose:
                        sys.stdout.write(tty_green + tty_bold + check_type
                           + " " + tty_normal)
                        sys.stdout.flush()
            except:
                pass
        else:
            found.append(check_type)
            if opt_verbose:
                sys.stdout.write(tty_blue + tty_bold + check_type \
                    + tty_normal + " ")
                sys.stdout.flush()

    if opt_verbose:
        sys.stdout.write("\n")
    found.sort()
    return found


#   +----------------------------------------------------------------------+
#   |                    ____ _           _                                |
#   |                   / ___| |_   _ ___| |_ ___ _ __                     |
#   |                  | |   | | | | / __| __/ _ \ '__|                    |
#   |                  | |___| | |_| \__ \ ||  __/ |                       |
#   |                   \____|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

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


#   +----------------------------------------------------------------------+
#   |          _   _           _       _               _                   |
#   |         | | | | ___  ___| |_ ___| |__   ___  ___| | _____            |
#   |         | |_| |/ _ \/ __| __/ __| '_ \ / _ \/ __| |/ / __|           |
#   |         |  _  | (_) \__ \ || (__| | | |  __/ (__|   <\__ \           |
#   |         |_| |_|\___/|___/\__\___|_| |_|\___|\___|_|\_\___/           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


# Returns check table for a specific host
# Format: ( checkname, item ) -> (params, description )

# Keep a global cache of per-host-checktables, since this
# operation is quite lengthy.
g_check_table_cache = {}
# A further cache splits up all checks into single-host-entries
# and those possibly matching multiple hosts. The single host entries
# are used in the autochecks and assumed be make up the vast majority.
g_singlehost_checks = None
g_multihost_checks = None
def get_check_table(hostname):
    global g_singlehost_checks
    global g_multihost_checks

    # speed up multiple lookup of same host
    if hostname in g_check_table_cache:
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
        if len(entry) == 4:
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
    for entry in g_singlehost_checks.get(hostname, []):
        handle_entry(entry)

    for entry in g_multihost_checks:
        handle_entry(entry)

    # Now add checks a cluster might receive from its nodes
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            node_checks = g_singlehost_checks.get(node, [])
            for nodename, checkname, item, params in node_checks:
                descr = service_description(checkname, item)
                if hostname == host_of_clustered_service(node, descr):
                    handle_entry((hostname, checkname, item, params))


    # Remove dependencies to non-existing services
    all_descr = set([ descr for ((checkname, item), (params, descr, deps)) in check_table.items() ])
    for (checkname, item), (params, descr, deps) in check_table.items():
        deeps = deps[:]
        del deps[:]
        for d in deeps:
            if d in all_descr:
                deps.append(d)

    g_check_table_cache[hostname] = check_table
    return check_table


def get_sorted_check_table(hostname):
    # Convert from dictionary into simple tuple list. Then sort
    # it according to the service dependencies.
    unsorted = [ (checkname, item, params, descr, deps)
                 for ((checkname, item), (params, descr, deps))
                 in get_check_table(hostname).items() ]
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
# HACK:
special_agent_dir = agents_dir + "/special"
if local_agents_dir:
    special_agent_local_dir = local_agents_dir + "/special"
else:
    special_agent_local_dir = None

def get_datasource_program(hostname, ipaddress):
    # First check WATO-style special_agent rules
    for agentname, ruleset in special_agents.items():
        params = host_extra_conf(hostname, ruleset)
        if params: # rule match!
            # Create command line using the special_agent_info
            cmd_arguments = special_agent_info[agentname](params[0], hostname, ipaddress)
            if special_agent_local_dir and \
                os.path.exists(special_agent_local_dir + "/agent_" + agentname):
                path = special_agent_local_dir + "/agent_" + agentname
            else:
                path = special_agent_dir + "/agent_" + agentname
            return path + " " + cmd_arguments

    programs = host_extra_conf(hostname, datasource_programs)
    if len(programs) == 0:
        return None
    else:
        return programs[0].replace("<IP>", ipaddress).replace("<HOST>", hostname)

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

    if opt_verbose:
        print "Updating DNS cache..."
    for hostname in all_active_hosts() + all_active_clusters():
        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        lookup_ipaddress(hostname)



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
        descr_format = check_info[check_type]["service_description"]

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.

    if type(item) == str:
        # Remove characters from item name that are banned by Nagios
        item_safe = "".join([ c for c in item if c not in nagios_illegal_chars ])
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


#   +----------------------------------------------------------------------+
#   |    ____             __ _                     _               _       |
#   |   / ___|___  _ __  / _(_) __ _    ___  _   _| |_ _ __  _   _| |_     |
#   |  | |   / _ \| '_ \| |_| |/ _` |  / _ \| | | | __| '_ \| | | | __|    |
#   |  | |__| (_) | | | |  _| | (_| | | (_) | |_| | |_| |_) | |_| | |_     |
#   |   \____\___/|_| |_|_| |_|\__, |  \___/ \__,_|\__| .__/ \__,_|\__|    |
#   |                          |___/                  |_|                  |
#   +----------------------------------------------------------------------+

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

def parse_hostname_list(args):
    valid_hosts = all_active_hosts() + all_active_clusters()
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
    return list(set(cgrs))

def host_contactgroups_nag(hostlist):
    cgrs = host_contactgroups_of(hostlist)
    if len(cgrs) > 0:
        return "    contact_groups " + ",".join(cgrs) + "\n"
    else:
        return ""

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
    else:
        value = "ping"

    if value == "ping":
        ping_args = check_icmp_arguments(hostname)
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



def check_icmp_arguments(hostname):
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
                reg = compiled_regexes.get(pattern)
                if not reg:
                    reg = re.compile(pattern)
                    compiled_regexes[pattern] = reg
                matchobject = reg.search(servicedesc)
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


# Compute list of service_groups or contact_groups of service
# conf is either service_groups or service_contactgroups
def service_extra_conf(hostname, service, conf):
    entries = []
    for entry in conf:
        entry, rule_options = get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            item, hostlist, servlist = entry
            tags = []
        elif len(entry) == 4:
            item, tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service configuration list: must have 3 or 4 elements" % (entry,))

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname) and \
           in_extraconf_servicelist(servlist, service):
            entries.append(item)
    return entries



# Entries in list are (tagged) hostnames that must equal the
# (untagged) hostname. Expressions beginning with ! are negated: if
# they match, the item is excluded from the list. Also the three
# special tags '@all', '@clusters', '@physical' are allowed.
def in_extraconf_hostlist(hostlist, hostname):

    # Migration help: print error if old format appears in config file
    if len(hostlist) == 1 and hostlist[0] == "":
        raise MKGeneralException('Invalid empty entry [ "" ] in configuration')

    for hostentry in hostlist:
        if len(hostentry) == 0:
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            ic = is_cluster(hostname)
            if hostentry == '@cluster' and ic:
                return True
            elif hostentry == '@physical' and not ic:
                return True

        # Allow negation of hostentry with prefix '!'
        elif hostentry[0] == '!':
            hostentry = hostentry[1:]
            negate = True
        else:
            negate = False

        if hostname == strip_tags(hostentry):
            return not negate

    return False

def in_extraconf_servicelist(list, item):
    for pattern in list:
        # Allow negation of pattern with prefix '!'
        if len(pattern) > 0 and pattern[0] == '!':
            pattern = pattern[1:]
            negate = True
        else:
            negate = False

        reg = compiled_regexes.get(pattern)
        if not reg:
            reg = re.compile(pattern)
            compiled_regexes[pattern] = reg
        if reg.match(item):
            return not negate

    # no match in list -> negative answer
    return False

# NEW IMPLEMENTATION
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

    if filesystem_levels != []:
        raise MKGeneralException("filesystem_levels is not longer supported.\n"
                "Please use check_parameters instead.\n"
                "Please refer to documentation:\n"
                " --> http://mathias-kettner.de/checkmk_check_parameters.html\n")

    output_conf_header(outfile)
    if hostnames == None:
        hostnames = all_hosts_untagged + all_active_clusters()

    for hostname in hostnames:
        create_nagios_config_host(outfile, hostname)

    create_nagios_config_hostgroups(outfile)
    create_nagios_config_servicegroups(outfile)
    create_nagios_config_contactgroups(outfile)
    create_nagios_config_commands(outfile)
    create_nagios_config_timeperiods(outfile)
    create_nagios_config_contacts(outfile)

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

    host_checks = get_check_table(hostname).items()
    host_checks.sort() # Create deterministic order
    aggregated_services_conf = set([])
    do_aggregation = host_is_aggregated(hostname)
    have_at_least_one_service = False
    used_descriptions = {}
    for ((checkname, item), (params, description, deps)) in host_checks:
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
        # Inventory checks - if user has configured them. Not for clusters.
        if inventory_check_interval and not is_cluster(hostname) \
            and not service_ignored(hostname,None,'Check_MK inventory'):
            outfile.write("""
define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  normal_check_interval\t\t%d
  retry_check_interval\t\t%d
%s  service_description\t\tCheck_MK inventory
}

define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\tCheck_MK
  dependent_host_name\t\t%s
  dependent_service_description\tCheck_MK inventory
}
""" % (inventory_check_template, hostname, inventory_check_interval, inventory_check_interval,
       extra_service_conf_of(hostname, "Check_MK inventory"),
       service_dependency_template, hostname, hostname))

    # legacy checks via legacy_checks
    legchecks = host_extra_conf(hostname, legacy_checks)
    if len(legchecks) > 0:
        outfile.write("\n\n# Legacy checks\n")
    for command, description, has_perfdata in legchecks:
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
            description = act_info["service_description"](params)

            if do_omit_service(hostname, description):
                continue

            # compute argument, and quote ! and \ for Nagios
            args = act_info["argument_function"](params).replace("\\", "\\\\").replace("!", "\\!")

            if description in used_descriptions:
                cn, it = used_descriptions[description]
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
""" % (template, hostname, make_utf8(description), simulate_command(command), extraconf))

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
            description = entry["service_description"]
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if do_omit_service(hostname, description):
                continue

            if command_line:
                command_line = autodetect_plugin(command_line)

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

""" % (pingonly_template, ping_command, check_icmp_arguments(hostname), extra_service_conf_of(hostname, "PING"), hostname))

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

def create_nagios_config_contacts(outfile):
    if len(contacts) > 0:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Contact definitions (controlled by variable 'contacts')\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        cnames = contacts.keys()
        cnames.sort()
        for cname in cnames:
            contact = contacts[cname]
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
            not_enabled = contact.get("notifications_enabled", True)
            for what in [ "host", "service" ]:
                no = contact.get(what + "_notification_options", "")
                if not no or not not_enabled:
                    outfile.write("  %s_notifications_enabled\t0\n" % what)
                    no = "n"
                outfile.write("  %s_notification_options\t%s\n" % (what, ",".join(list(no))))
                outfile.write("  %s_notification_period\t%s\n" % (what, contact.get("notification_period", "24X7")))
                outfile.write("  %s_notification_commands\t%s\n" % (what, contact.get("%s_notification_commands" % what, "check-mk-notify")))

            outfile.write("  contactgroups\t\t\t%s\n" % ", ".join(cgrs))
            outfile.write("}\n\n")


# Quote string for use in a nagios command execution.
# Please note that also quoting for ! and \ vor Nagios
# itself takes place here.
def quote_nagios_string(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "'\"'\"'").replace('!', '\\!') + "'"




#   +----------------------------------------------------------------------+
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+


def inventorable_checktypes(what): # snmp, tcp, all
    checknames = [ k for k in check_info.keys()
                   if check_info[k]["inventory_function"] != None
                   and (what == "all"
                        or check_uses_snmp(k) == (what == "snmp"))
                 ]
    checknames.sort()
    return checknames

def checktype_ignored_for_host(host, checktype):
    if checktype in ignored_checktypes:
        return True
    ignored = host_extra_conf(host, ignored_checks)
    for e in ignored:
        if checktype == e or (type(e) == list and checktype in e):
            return True
    return False

def do_snmp_scan(hostnamelist, check_only=False, include_state=False):
    if hostnamelist == []:
        hostnamelist = all_hosts_untagged

    result = []
    for hostname in hostnamelist:
        if not is_snmp_host(hostname):
            continue
        try:
            ipaddress = lookup_ipaddress(hostname)
        except:
            sys.stdout.write("Cannot resolve %s into IP address. Skipping.\n" % hostname)
            continue
        checknames = snmp_scan(hostname, ipaddress)
        for checkname in checknames:
            if opt_debug:
                sys.stdout.write("Trying inventory for %s on %s\n" % (checkname, hostname))
            result += make_inventory(checkname, [hostname], check_only, include_state)
    return result



def make_inventory(checkname, hostnamelist, check_only=False, include_state=False):
    try:
        inventory_function = check_info[checkname]["inventory_function"]
        if inventory_function == None:
            inventory_function = no_inventory_possible
    except KeyError:
        sys.stderr.write("No such check type '%s'. Try check_mk -L.\n" % checkname)
        sys.exit(1)

    is_snmp_check = check_uses_snmp(checkname)

    newchecks = []
    newitems = []   # used by inventory check to display unchecked items
    count_new = 0
    checked_hosts = []

    # if no hostnamelist is specified, we use all hosts
    if not hostnamelist or len(hostnamelist) == 0:
        global opt_use_cachefile
        opt_use_cachefile = True
        hostnamelist = all_hosts_untagged

    try:
        for host in hostnamelist:

            # Skip SNMP checks on non-SNMP hosts
            if is_snmp_check and not is_snmp_host(host):
                continue

            # The decision wether to contact the agent via TCP
            # is done in get_realhost_info(). This is due to
            # the possibility that piggyback data from other
            # hosts is available.

            if is_cluster(host):
                sys.stderr.write("%s is a cluster host and cannot be inventorized.\n" % host)
                continue

            # host is either hostname or "hostname/ipaddress"
            s = host.split("/")
            hostname = s[0]
            if len(s) == 2:
                ipaddress = s[1]
            else:
                # try to resolve name into ip address
                if not opt_no_tcp:
                    try:
                        ipaddress = lookup_ipaddress(hostname)
                    except:
                        sys.stderr.write("Cannot resolve %s into IP address.\n" % hostname)
                        continue
                else:
                    ipaddress = None # not needed, not TCP used

            # Make hostname available as global variable in inventory functions
            # (used e.g. by ps-inventory)
            global g_hostname
            g_hostname = hostname

            # On --no-tcp option skip hosts without cache file
            if opt_no_tcp:
                if opt_no_cache:
                    sys.stderr.write("You allowed me neither TCP nor cache. Bailing out.\n")
                    sys.exit(4)

                cachefile = tcp_cache_dir + "/" + hostname
                if not os.path.exists(cachefile):
                    if opt_verbose:
                        sys.stderr.write("No cachefile %s. Skipping this host.\n" % cachefile)
                    continue

            checked_hosts.append(hostname)

            checkname_base = checkname.split('.')[0]    # make e.g. 'lsi' from 'lsi.arrays'
            try:
                info = get_realhost_info(hostname, ipaddress, checkname_base, inventory_max_cachefile_age, True)
                # Add information about nodes if check wants this
                if check_info[checkname]["node_info"]:
                    if clusters_of(hostname):
                        add_host = hostname
                    else:
                        add_host = None
                    info = [ [add_host] + line for line in info ]
            except MKAgentError, e:
                # This special handling is needed for the inventory check. It needs special
                # handling for WATO.
                if check_only and not include_state and str(e):
                    raise
		elif not include_state and str(e):
		    sys.stderr.write("Host '%s': %s\n" % (hostname, str(e)))
                elif include_state and str(e): # WATO automation. Abort
                    raise
                continue
            except MKSNMPError, e:
                # This special handling is needed for the inventory check. It needs special
                # handling for WATO.
                if check_only and not include_state and str(e):
                    raise
		elif not include_state and str(e):
                    sys.stderr.write("Host '%s': %s\n" % (hostname, str(e)))
                continue
            except Exception, e:
                if check_only or opt_debug:
                    raise
                sys.stderr.write("Cannot get information from host '%s': %s\n" % (hostname, e))
                continue

            if info == None: # No data for this check type
                continue
            try:
                # Check number of arguments of inventory function
                if len(inspect.getargspec(inventory_function)[0]) == 2:
                    inventory = inventory_function(checkname, info) # inventory is a list of pairs (item, current_value)
                else:
                    # New preferred style since 1.1.11i3: only one argument: info
                    inventory = inventory_function(info)

                if inventory == None: # tolerate if function does no explicit return
                    inventory = []
            except Exception, e:
                if opt_debug:
                    sys.stderr.write("Exception in inventory function of check type %s\n" % checkname)
                    raise
                if opt_verbose:
		    sys.stderr.write("%s: Invalid output from agent or invalid configuration: %s\n" % (hostname, e))
                continue

            if not isinstance(inventory, list):
                sys.stderr.write("%s: Check %s returned invalid inventory data: %s\n" %
                                                    (hostname, checkname, repr(inventory)))
                continue

            for entry in inventory:
                state_type = "new" # assume new, change later if wrong

                if not isinstance(entry, tuple):
                    sys.stderr.write("%s: Check %s returned invalid inventory data (entry not a tuple): %s\n" %
                                                                         (hostname, checkname, repr(inventory)))
                    continue

                if len(entry) == 2: # comment is now obsolete
                    item, paramstring = entry
                else:
                    try:
                        item, comment, paramstring = entry
                    except ValueError:
                        sys.stderr.write("%s: Check %s returned invalid inventory data (not 2 or 3 elements): %s\n" %
                                                                               (hostname, checkname, repr(inventory)))
                        continue

                description = service_description(checkname, item)
                # make sanity check
                if len(description) == 0:
                    sys.stderr.write("%s: Check %s returned empty service description - ignoring it.\n" %
                                                    (hostname, checkname))
                    continue


                # Find logical host this check belongs to. The service might belong to a cluster.
                hn = host_of_clustered_service(hostname, description)

                # Now compare with already known checks for this host (from
                # previous inventory or explicit checks). Also drop services
                # the user wants to ignore via 'ignored_services'.
                checktable = get_check_table(hn)
                checked_items = [ i for ( (cn, i), (par, descr, deps) ) \
                                  in checktable.items() if cn == checkname ]
                if item in checked_items:
                    if include_state:
                        state_type = "old"
                    else:
                        continue # we have that already

                if service_ignored(hn, checkname, description):
                    if include_state:
                        if state_type == "old":
                            state_type = "obsolete"
                        else:
                            state_type = "ignored"
                    else:
                        continue # user does not want this item to be checked

                newcheck = '  ("%s", "%s", %r, %s),' % (hostname, checkname, item, paramstring)
                newcheck += "\n"
                if newcheck not in newchecks: # avoid duplicates if inventory outputs item twice
                    newchecks.append(newcheck)
                    if include_state:
                        newitems.append( (hostname, checkname, item, paramstring, state_type) )
                    else:
                        newitems.append( (hostname, checkname, item) )
                    count_new += 1


    except KeyboardInterrupt:
        sys.stderr.write('<Interrupted>\n')


    if not check_only:
        if newchecks != []:
            filename = autochecksdir + "/" + checkname + "-" + time.strftime("%Y-%m-%d_%H.%M.%S")
            while os.path.exists(filename + ".mk"): # in case of more than one file per second and checktype...
                filename += ".x"
            filename += ".mk"
            if not os.path.exists(autochecksdir):
                os.makedirs(autochecksdir)
            file(filename, "w").write('# %s\n[\n%s]\n' % (filename, ''.join(newchecks)))
            sys.stdout.write('%-30s ' % (tty_cyan + tty_bold + checkname + tty_normal))
            sys.stdout.write('%s%d new checks%s\n' % (tty_bold + tty_green, count_new, tty_normal))

    return newitems


def check_inventory(hostname):
    newchecks = []
    newitems = []
    total_count = 0
    is_snmp = is_snmp_host(hostname)
    is_tcp  = is_tcp_host(hostname)
    check_table = get_check_table(hostname)
    hosts_checktypes = set([ ct for (ct, item), params in check_table.items() ])
    try:
        for ct in inventorable_checktypes("all"):
            if check_uses_snmp(ct) and not is_snmp:
                continue # Skip SNMP checks on non-SNMP hosts
            elif check_uses_snmp(ct) and ct not in hosts_checktypes:
 		continue # Do not look for new SNMP services (maybe change in future)
            elif not check_uses_snmp(ct) and not is_tcp:
                continue # Skip TCP checks on non-TCP hosts

            new = make_inventory(ct, [hostname], True)
            newitems += new
            count = len(new)
            if count > 0:
                newchecks.append((ct, count))
                total_count += count
        if total_count > 0:
            info = ", ".join([ "%s:%d" % (ct, count) for ct,count in newchecks ])
            statustext = { 0 : "OK", 1: "WARNING", 2:"CRITICAL" }.get(inventory_check_severity, "UNKNOWN")
            sys.stdout.write("%s - %d unchecked services (%s)\n" % (statustext, total_count, info))
            # Put detailed list into long plugin output
            for hostname, checkname, item in newitems:
                sys.stdout.write("%s: %s\n" % (checkname, service_description(checkname, item)))
            sys.exit(inventory_check_severity)
        else:
            sys.stdout.write("OK - no unchecked services found\n")
            sys.exit(0)
    except SystemExit, e:
        raise e
    except Exception, e:
        if opt_debug:
            raise
        sys.stdout.write("UNKNOWN - %s\n" % (e,))
        sys.exit(3)


def service_ignored(hostname, checktype, service_description):
    if checktype and checktype in ignored_checktypes:
        return True
    if in_boolean_serviceconf_list(hostname, service_description, ignored_services):
        return True
    if checktype and checktype_ignored_for_host(hostname, checktype):
        return True
    return False


def in_boolean_serviceconf_list(hostname, service_description, conflist):
    for entry in conflist:
        entry, rule_options = get_rule_options(entry)
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

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
           in_extraconf_hostlist(hostlist, hostname) and \
           in_extraconf_servicelist(servlist, service_description):
            if opt_verbose:
                print "Ignoring service '%s' on host %s." % (service_description, hostname)
            return not negate
    return False # no match. Do not ignore


# Remove all autochecks of certain types of a certain host
def remove_autochecks_of(hostname, checktypes = None): # None = all
    removed = 0
    for fn in glob.glob(autochecksdir + "/*.mk"):
        if opt_debug:
            sys.stdout.write("Scanning %s...\n" % fn)
        lines = []
        count = 0
        for line in file(fn):
            # hostname and check type can be quoted with ' or with "
            double_quoted = line.replace("'", '"').lstrip()
            if double_quoted.startswith('("'):
                count += 1
                splitted = double_quoted.split('"')
                if splitted[1] != hostname or (checktypes != None and splitted[3] not in checktypes):
                    if splitted[3] not in check_info:
                        sys.stderr.write('Removing unimplemented check %s\n' % splitted[3])
                        continue
                    lines.append(line)
                else:
                    removed += 1
        if len(lines) == 0:
            if opt_verbose:
                sys.stdout.write("Deleting %s.\n" % fn)
            os.remove(fn)
        elif count > len(lines):
            if opt_verbose:
                sys.stdout.write("Removing %d checks from %s.\n" % (count - len(lines), fn))
            f = file(fn, "w+")
            f.write("[\n")
            for line in lines:
                f.write(line)
            f.write("]\n")

    return removed

def remove_all_autochecks():
    for f in glob.glob(autochecksdir + '/*.mk'):
        if opt_verbose:
            sys.stdout.write("Deleting %s.\n" % f)
        os.remove(f)

def reread_autochecks():
    global checks
    checks = checks[len(autochecks):]
    read_all_autochecks()
    checks = autochecks + checks

#   +----------------------------------------------------------------------+
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+

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
    host_checks = get_sorted_check_table(hostname)
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
opt_verbose = '-v' in sys.argv
opt_debug   = '-d' in sys.argv

# make sure these names are defined (even if never needed)
no_inventory_possible = None
""")

    # Compile in all neccessary global variables
    output.write("\n# Global variables\n")
    for var in [ 'check_mk_version', 'tcp_connect_timeout', 'agent_min_version',
                 'perfdata_format', 'aggregation_output_format',
                 'aggr_summary_hostname', 'nagios_command_pipe_path',
                 'check_result_path', 'check_submission', 'monitoring_core',
                 'var_dir', 'counters_directory', 'tcp_cache_dir', 'tmp_dir',
                 'snmpwalks_dir', 'check_mk_basedir', 'nagios_user', 'rrd_path', 'rrdcached_socket',
                 'omd_root',
                 'www_group', 'cluster_max_cachefile_age', 'check_max_cachefile_age',
                 'piggyback_max_cachefile_age',
                 'simulation_mode', 'agent_simulator', 'aggregate_check_mk', 'debug_log',
                 'check_mk_perfdata_with_times', 'livestatus_unix_socket',
                 'has_inline_snmp', 'use_inline_snmp',
                 ]:
        output.write("%s = %r\n" % (var, globals()[var]))

    output.write("\n# Checks for %s\n\n" % hostname)
    output.write("def get_sorted_check_table(hostname):\n    return %r\n\n" % check_table)

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

    # snmp hosts
    output.write("def is_snmp_host(hostname):\n   return %r\n\n" % is_snmp_host(hostname))
    output.write("def is_tcp_host(hostname):\n   return %r\n\n" % is_tcp_host(hostname))
    output.write("def is_usewalk_host(hostname):\n   return %r\n\n" % is_usewalk_host(hostname))
    if has_inline_snmp and use_inline_snmp:
        output.write("def is_snmpv2c_host(hostname):\n   return %r\n\n" % is_snmpv2c_host(hostname))
        output.write("def is_bulkwalk_host(hostname):\n   return %r\n\n" % is_bulkwalk_host(hostname))
        output.write("def snmp_timing_of(hostname):\n   return %r\n\n" % snmp_timing_of(hostname))
        output.write("def snmp_credentials_of(hostname):\n   return %r\n\n" % snmp_credentials_of(hostname))
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
    output.write("    do_check(%r, %r)\n" % (hostname, ipaddress))
    output.write("except SystemExit, e:\n")
    output.write("    sys.exit(e.code)\n")
    output.write("except Exception, e:\n")
    output.write("    import traceback, pprint\n")

    # status output message
    output.write("    sys.stdout.write(\"UNKNOWN - Exception in precompiled check: %s (details in long output)\\n\" % e)\n")

    # generate traceback for long output
    output.write("    sys.stdout.write(\"Traceback: %s\\n\" % traceback.format_exc())\n")

    # debug logging
    output.write("    if debug_log:\n")
    output.write("        l = file(debug_log, \"a\")\n")
    output.write("        l.write((\"Exception in precompiled check:\\n\"\n")
    output.write("                \"  Check_MK Version: %s\\n\"\n")
    output.write("                \"  Date:             %s\\n\"\n")
    output.write("                \"  Host:             %s\\n\"\n")
    output.write("                \"  %s\\n\") % (\n")
    output.write("                check_mk_version,\n")
    output.write("                time.strftime(\"%Y-%d-%m %H:%M:%S\"),\n")
    output.write("                \"%s\",\n" % hostname)
    output.write("                traceback.format_exc().replace('\\n', '\\n      ')))\n")
    output.write("        l.close()\n")

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


#   +----------------------------------------------------------------------+
#   |                  __  __                         _                    |
#   |                 |  \/  | __ _ _ __  _   _  __ _| |                   |
#   |                 | |\/| |/ _` | '_ \| | | |/ _` | |                   |
#   |                 | |  | | (_| | | | | |_| | (_| | |                   |
#   |                 |_|  |_|\__,_|_| |_|\__,_|\__,_|_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

opt_nowiki   = False

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
        parsed = parse_man_header(checkname, path)
        cat = parsed["catalog"]
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
    import subprocess
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
        sys.stderr.write("Section agents missing in man page of %s\n" % (checkname))
        sys.exit(1)
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
            print_splitline(title_color_left, "%-19s" % left, title_color_right, right)

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
        print_splitline(header_color_left, "Supported Agents:  ", header_color_right, ", ".join(ags))
        distro = header['distribution']
        if distro == 'check_mk':
            distro = "official part of Check_MK"
        print_splitline(header_color_left, "Distribution:      ", header_color_right, distro)
        print_splitline(header_color_left, "License:           ", header_color_right, header['license'])

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

#   +----------------------------------------------------------------------+
#   |                  ____             _                                  |
#   |                 | __ )  __ _  ___| | ___   _ _ __                    |
#   |                 |  _ \ / _` |/ __| |/ / | | | '_ \                   |
#   |                 | |_) | (_| | (__|   <| |_| | |_) |                  |
#   |                 |____/ \__,_|\___|_|\_\\__,_| .__/                   |
#   |                                             |_|                      |
#   +----------------------------------------------------------------------+

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
        d = remove_autochecks_of(host)
        if d > 0:
            flushed = True
            sys.stdout.write(tty_bold + tty_cyan + " autochecks(%d)" % d)

        if not flushed:
            sys.stdout.write("(nothing)")


        sys.stdout.write(tty_normal + "\n")


#   +----------------------------------------------------------------------+
#   |   __  __       _        __                  _   _                    |
#   |  |  \/  | __ _(_)_ __  / _|_   _ _ __   ___| |_(_) ___  _ __  ___    |
#   |  | |\/| |/ _` | | '_ \| |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|   |
#   |  | |  | | (_| | | | | |  _| |_| | | | | (__| |_| | (_) | | | \__ \   |
#   |  |_|  |_|\__,_|_|_| |_|_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

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

def do_snmptranslate(walk):
    walk = walk[0]

    path_walk = "%s/%s" % (snmpwalks_dir, walk)
    if not os.path.exists(path_walk):
        print "Walk does not exist"
        return

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
                result_lines.append((line, lines[idx]))

            # Add missing fields one by one
            for line in lines[len(result_lines):]:
                result_lines.extend(translate([line]))
        except Exception, e:
            print e

        return result_lines


    # Translate n-oid's per cycle
    entries_per_cycle = 50
    translated_lines = []

    walk_lines = file(path_walk).readlines()
    sys.stderr.write("Processing %d lines (%d per dot)\n" %  (len(walk_lines), entries_per_cycle))
    for i in range(0, len(walk_lines), entries_per_cycle):
        sys.stderr.write(".")
        sys.stderr.flush()
        process_lines = walk_lines[i:i+entries_per_cycle]
        translated_lines.extend(translate(process_lines))
    sys.stderr.write("\n")

    # Output formatted
    longest_translation = 40
    for translation, line in translated_lines:
        longest_translation = max(longest_translation, len(translation))

    format_string = "%%-%ds %%s" % longest_translation
    for translation, line in translated_lines:
        sys.stdout.write(format_string % (translation, line))

def do_snmpwalk(hostnames):
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
    if opt_verbose:
        sys.stdout.write("%s:\n" % hostname)
    ip = lookup_ipaddress(hostname)

    out = file(filename, "w")
    for oid in [
            ".1.3.6.1.2.1", # SNMPv2-SMI::mib-2
            ".1.3.6.1.4.1"  # SNMPv2-SMI::enterprises
          ]:
        if opt_verbose:
            sys.stdout.write("Walk on \"%s\"..." % oid)
            sys.stdout.flush()

        if has_inline_snmp and use_inline_snmp:
            results = inline_snmpwalk_on_suboid(hostname, oid, strip_values = False)
        else:
            results = snmpwalk_on_suboid(hostname, ip, oid)

        for oid, value in results:
            out.write("%s %s\n" % (oid, value))

        if opt_verbose:
            sys.stdout.write("%d variables.\n" % len(results))

    out.close()
    if opt_verbose:
        sys.stdout.write("Successfully Wrote %s%s%s.\n" % (tty_bold, filename, tty_normal))

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
    print tty_yellow + "Host groups:            " + tty_normal + ", ".join(hostgroups_of(hostname))
    print tty_yellow + "Contact groups:         " + tty_normal + ", ".join(host_contactgroups_of([hostname]))

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
            if is_bulkwalk_host(hostname):
                bulk = "yes"
            else:
                bulk = "no"
            portinfo = snmp_port_of(hostname)
            if portinfo == None:
                portinfo = 'default'
            agenttypes.append("SNMP (community: '%s', bulk walk: %s, port: %s, inline: %s)" %
                (credentials, bulk, portinfo, inline))

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
 cmk [-u] -I [HOST ..]                inventory - find new services
 cmk [-u] -II ...                     renew inventory, drop old services
 cmk -u, --cleanup-autochecks         reorder autochecks files
 cmk -N [HOSTS...]                    output Nagios configuration
 cmk -B                               create configuration for core
 cmk -C, --compile                    precompile host checks
 cmk -U, --update                     precompile + create config for core
 cmk -O, --reload                     precompile + config + core reload
 cmk -R, --restart                    precompile + config + core restart
 cmk -D, --dump [H1 H2 ..]            dump all or some hosts
 cmk -d HOSTNAME|IPADDRESS            show raw information from agent
 cmk --check-inventory HOSTNAME       check for items not yet checked
 cmk --update-dns-cache               update IP address lookup cache
 cmk --list-hosts [G1 G2 ...]         print list of hosts
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
 cmk --snmpwalk HOST1 HOST2 ...       Do snmpwalk on host
 cmk --snmptranslate HOST             Do snmptranslate on walk
 cmk --snmpget OID HOST1 HOST2 ...    Fetch single OIDs and output them
 cmk --scan-parents [HOST1 HOST2...]  autoscan parents, create conf.d/parents.mk
 cmk -P, --package COMMAND            do package operations
 cmk --localize COMMAND               do localization operations
 cmk --notify                         used to send notifications from core
 cmk --create-rrd [--keepalive|SPEC]  create round robin database
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
  --checks A,..  restrict checks/inventory to specified checks (tcp/snmp/check type)
  --keepalive    used by Check_MK Mirco Core: run check and --notify in continous
                 mode. Read data from stdin and von from cmd line and environment
  --cmc-file=X   relative filename for CMC config file (used by -B/-U)

NOTES:
  -I can be restricted to certain check types. Write '--checks df -I' if you
  just want to look for new filesystems. Use 'check_mk -L' for a list
  of all check types. Use 'tcp' for all TCP based checks and 'snmp' for
  all SNMP based checks.

  -II does the same as -I but deletes all existing checks of the
  specified types and hosts.

  -u, --cleanup-autochecks resorts all checks found by inventory
  into per-host files. It can be used as an options to -I or as
  a standalone operation.

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

  --check-inventory make check_mk behave as monitoring plugins that
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

  --flush deletes all runtime data belonging to a host (not
  inventory data). This includes the state of performance counters,
  cached agent output,  and logfiles. Precompiled host checks
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

  --snmptranslate does not contact the host again, but reuses the hosts
  walk from the directory %s.%s

  --scan-parents uses traceroute in order to automatically detect
  hosts's parents. It creates the file conf.d/parents.mk which
  defines gateway hosts and parent declarations.

  The core can call check_mk without options and the hostname and its IP
  address as arguments. Much faster is using precompiled host checks,
  though.


""" % (check_mk_configfile,
       precompiled_hostchecks_dir,
       snmpwalks_dir,
       snmpwalks_dir,
       local_mibs_dir and ("\n  You can add further mibs to %s" % local_mibs_dir) or "",
       )


def do_create_config():
    sys.stdout.write("Generating configuration for core (type %s)..." % monitoring_core)
    sys.stdout.flush()
    if monitoring_core == "cmc":
        do_create_cmc_config(opt_cmc_relfilename)
    else:
        out = file(nagios_objects_file, "w")
        create_nagios_config(out)
    sys.stdout.write(tty_ok + "\n")

def do_output_nagios_conf(args):
    if len(args) == 0:
        args = None
    create_nagios_config(sys.stdout, args)

def do_precompile_hostchecks():
    sys.stdout.write("Precompiling host checks...")
    sys.stdout.flush()
    precompile_hostchecks()
    sys.stdout.write(tty_ok + "\n")


def do_update(with_precompile):
    try:
        do_create_config()
        if with_precompile and monitoring_core != "cmc":
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


def do_restart_core(only_reload):
    action = only_reload and "load" or "start"
    sys.stdout.write("Re%sing monitoring core..." % action)
    sys.stdout.flush()
    if monitoring_core == "nagios":
        os.putenv("CORE_NOVERIFY", "yes")
        command = nagios_startscript + " re%s 2>&1" % action
    else:
        command = "omd re%s cmc 2>&1" % action

    process = os.popen(command, "r")
    output = process.read()
    if process.close():
        sys.stdout.write("ERROR: %s\n" % output)
        raise MKGeneralException("Cannot re%s the monitoring core: %s" % (action, output))
    else:
        sys.stdout.write(tty_ok + "\n")

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
            do_create_config()
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
            if monitoring_core != "cmc":
                do_precompile_hostchecks()
            do_restart_core(only_reload)
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

def do_cleanup_autochecks():
    # 1. Read in existing autochecks
    hostdata = {}
    os.chdir(autochecksdir)
    checks = 0
    for fn in glob.glob("*.mk"):
        if opt_debug:
            sys.stdout.write("Scanning %s...\n" % fn)
        for line in file(fn):
            testline = line.lstrip().replace("'", '"')
            if testline.startswith('("'):
                splitted = testline.split('"')
                hostname = splitted[1]
                hostchecks = hostdata.get(hostname, [])
                hostchecks.append(line)
                checks += 1
                hostdata[hostname] = hostchecks
    if opt_verbose:
        sys.stdout.write("Found %d checks from %d hosts.\n" % (checks, len(hostdata)))

    # 2. Write out new autochecks.
    newfiles = set([])
    for host, lines in hostdata.items():
        lines.sort()
        fn = host.replace(":","_") + ".mk"
        if opt_verbose:
            sys.stdout.write("Writing %s: %d checks\n" % (fn, len(lines)))
        newfiles.add(fn)
        f = file(fn, "w+")
        f.write("[\n")
        for line in lines:
            f.write(line)
        f.write("]\n")

    # 3. Remove obsolete files
    for f in glob.glob("*.mk"):
        if f not in newfiles:
            if opt_verbose:
                sys.stdout.write("Deleting %s\n" % f)
            os.remove(f)

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


# Diagnostic function for detecting global variables that have
# changed during checking. This is slow and canno be used
# in production mode.
def copy_globals():
    import copy
    global_saved = {}
    for varname, value in globals().items():
        # Some global caches are allowed to change.
        if varname not in [ "g_service_description", "g_multihost_checks", "g_check_table_cache", "g_singlehost_checks", "total_check_outout" ] \
            and type(value).__name__ not in [ "function", "module", "SRE_Pattern" ]:
            global_saved[varname] = copy.copy(value)
    return global_saved


def do_check_keepalive():
    global g_initial_times

    def check_timeout(signum, frame):
        raise MKCheckTimeout()

    signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc

    global total_check_output
    total_check_output = ""
    if opt_debug:
        before = copy_globals()

    ipaddress_cache = {}

    while True:
        cleanup_globals()
        hostname = sys.stdin.readline()
        g_initial_times = os.times()
        if not hostname:
            break
        hostname = hostname.strip()
        if hostname == "*":
            if opt_debug:
                sys.stdout.write("Restarting myself...\n")
            sys.stdout.flush()
            os.execvp("cmk", sys.argv)
        elif not hostname:
            break

        timeout = int(sys.stdin.readline())
        try: # catch non-timeout exceptions
            try: # catch timeouts
                signal.signal(signal.SIGALRM, check_timeout)
                signal.alarm(timeout)
                if ';' in hostname:
                    hostname, ipaddress = hostname.split(";", 1)
                elif hostname in ipaddress_cache:
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

                status = do_check(hostname, ipaddress)
                signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc
                signal.alarm(0)
            except MKCheckTimeout:
                signal.signal(signal.SIGALRM, signal.SIG_IGN) # Prevent ALRM from CheckHelper.cc
                status = 3
                total_check_output = "UNKNOWN - Check_MK timed out after %d seconds\n" % timeout

            sys.stdout.write("%03d\n%08d\n%s" %
                 (status, len(total_check_output), total_check_output))
            sys.stdout.flush()
            total_check_output = ""
            cleanup_globals()

            # Check if all global variables are clean, but only in debug mode
            if opt_debug:
                after = copy_globals()
                for varname, value in before.items():
                    if value != after[varname]:
                        sys.stderr.write("WARNING: global variable %s has changed: %r ==> %s\n"
                               % (varname, value, repr(after[varname])[:50]))
                new_vars = set(after.keys()).difference(set(before.keys()))
                if (new_vars):
                    sys.stderr.write("WARNING: new variable appeared: %s" % ", ".join(new_vars))

        except Exception, e:
            if opt_debug:
                raise
            sys.stdout.write("UNKNOWN - %s\n3\n" % e)




#   +----------------------------------------------------------------------+
#   |         ____                _                    __ _                |
#   |        |  _ \ ___  __ _  __| |   ___ ___  _ __  / _(_) __ _          |
#   |        | |_) / _ \/ _` |/ _` |  / __/ _ \| '_ \| |_| |/ _` |         |
#   |        |  _ <  __/ (_| | (_| | | (_| (_) | | | |  _| | (_| |         |
#   |        |_| \_\___|\__,_|\__,_|  \___\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+

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
            sys.stderr.write("Cannot read in configuration file %s:\n%s\n" % (_f, e))
            if __name__ == "__main__":
                sys.exit(3)
            else:
                raise

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
            sys.exit(4)
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
    checks = static + checks

    # Read autochecks and append them to explicit checks
    if with_autochecks:
        read_all_autochecks()
        checks = autochecks + checks

    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'autochecks', 'parts',
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

    # Convert www_group into numeric id
    global www_group
    if type(www_group) == str:
        try:
            import grp
            www_group = grp.getgrnam(www_group)[2]
        except Exception, e:
            sys.stderr.write("Cannot convert group '%s' into group id: %s\n" % (www_group, e))
            sys.stderr.write("Please set www_group to an existing group in main.mk.\n")
            sys.exit(3)

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

    # Load agent simulator if enabled in configuration
    if agent_simulator:
        execfile(modules_dir + "/agent_simulator.py", globals(), globals())


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


# read automatically generated checks. They are prepended to the check
# table: explicit user defined checks override automatically generated
# ones. Do not read in autochecks, if check_mk is called as module.
def read_all_autochecks():
    global autochecks
    autochecks = []
    for f in glob.glob(autochecksdir + '/*.mk'):
        try:
            autochecks += eval(file(f).read())
        except SyntaxError,e:
            if opt_verbose:
                sys.stderr.write("Syntax error in file %s: %s\n" % (f, e))
            if opt_debug:
                sys.exit(3)
        except Exception, e:
            if opt_verbose:
                sys.stderr.write("Error in file %s:\n%s\n" % (f, e))
            if opt_debug:
                sys.exit(3)

    # Exchange inventorized check parameters with those configured by
    # the user. Also merge with default levels for modern dictionary based checks.
    autochecks = [ (host, ct, it, compute_check_parameters(host, ct, it, par))
                   for (host, ct, it, par) in autochecks ]


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

#   +----------------------------------------------------------------------+
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+



# Do option parsing and execute main function -
# if check_mk is not called as module
if __name__ == "__main__":
    short_options = 'SHVLCURODMmd:Ic:nhvpXPuNB'
    long_options = [ "help", "version", "verbose", "compile", "debug",
                     "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
                     "flush", "package", "localize", "donate", "snmpwalk", "snmptranslate",
                     "usewalk", "scan-parents", "procs=", "automation=", "notify",
                     "snmpget=", "profile", "keepalive", "create-rrd",
                     "no-cache", "update", "restart", "reload", "dump", "fake-dns=",
                     "man", "nowiki", "config-check", "backup=", "restore=",
                     "check-inventory=", "paths", "cleanup-autochecks", "checks=",
                     "cmc-file=", "browse-man", "list-man", "update-dns-cache" ]

    non_config_options = ['-L', '--list-checks', '-P', '--package', '-M', '--notify',
                          '--man', '-V', '--version' ,'-h', '--help', '--automation']

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
    inventory_checks = None
    # Scan modifying options first (makes use independent of option order)
    for o,a in opts:
        if o in [ '-v', '--verbose' ]:
            opt_verbose = True
        elif o == '-c':
            check_mk_configfile = a
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
        elif o in [ '-u', '--cleanup-autochecks' ]:
            opt_cleanup_autochecks = True
        elif o == '--fake-dns':
            fake_dns = a
        elif o == '--keepalive':
            opt_keepalive = True
        elif o == '--usewalk':
            opt_use_snmp_walk = True
        elif o == '--procs':
            max_num_processes = int(a)
        elif o == '--nowiki':
            opt_nowiki = True
        elif o == '--debug':
            opt_debug = True
        elif o == '-I':
            seen_I += 1
        elif o == "--checks":
            inventory_checks = a
        elif o == "--cmc-file":
            opt_cmc_relfilename = a

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
                do_update(False)
                done = True
            elif o in [ '-C', '--compile' ]:
                precompile_hostchecks()
                done = True
            elif o in [ '-U', '--update' ] :
                do_update(True)
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
            elif o == '--list-hosts':
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
            elif o == '--check-inventory':
                check_inventory(a)
                done = True
            elif o == '--scan-parents':
                do_scan_parents(args)
                done = True
            elif o == '--automation':
                execfile(modules_dir + "/automation.py")
                do_automation(a, args)
                done = True
            elif o == '--notify':
                read_config_files(False, True)
                sys.exit(do_notify(args))
            elif o == '--create-rrd':
                read_config_files(False, True)
                execfile(modules_dir + "/rrd.py")
                do_create_rrd(args)
                done = True


    except MKGeneralException, e:
        sys.stderr.write("%s\n" % e)
        if opt_debug:
            raise
        sys.exit(3)

    if not done and seen_I > 0:

        hostnames = parse_hostname_list(args)
        # For clusters add their nodes to the list
        nodes = []
        for h in hostnames:
            nodes = nodes_of(h)
            if nodes:
                hostnames += nodes

        # Then remove clusters and make list unique
        hostnames = list(set([ h for h in hostnames if not is_cluster(h) ]))
        hostnames.sort()

        if opt_verbose:
            if len(hostnames) > 0:
                sys.stdout.write("Inventorizing %s.\n" % ", ".join(hostnames))
            else:
                sys.stdout.write("Inventorizing all hosts.\n")

        if inventory_checks:
            checknames = inventory_checks.split(",")

        # remove existing checks, if option -I is used twice
        if seen_I > 1:
            if inventory_checks == None:
                checknames = inventorable_checktypes("all")
            if len(hostnames) > 0:
                # Entries in hostnames that are either prefixed with @
                # or are no valid hostnames are considered to be tags.
                for host in hostnames:
                    remove_autochecks_of(host, checknames)
                    # If all nodes of a cluster are contained in the list, then
                    # also remove the autochecks of that cluster. Beware: a host
                    # can be part more multiple clusters
                    for clust in clusters_of(host):
                        missing = [] # collect nodes missing on the command line
                        for node in nodes_of(clust):
                            if node not in hostnames:
                                missing.append(node)

                        if len(missing) == 0:
                            if opt_verbose:
                                sys.stdout.write("All nodes of %s specified, dropping checks of %s, too.\n" % (clust, node))
                            remove_autochecks_of(clust, checknames)

                        else:
                            sys.stdout.write("Warning: %s is part of cluster %s, but you didn't specify %s as well.\nChecks on %s will be kept.\n" %
                            (host, clust, ",".join(missing), clust))

            else:
                for host in all_active_hosts() + all_active_clusters():
                    remove_autochecks_of(host, checknames)
            reread_autochecks()

        if inventory_checks == None:
            do_snmp_scan(hostnames)
            checknames = inventorable_checktypes("tcp")

        for checkname in checknames:
            make_inventory(checkname, hostnames, False)

        # -u, --cleanup-autochecks called in stand alone mode
        if opt_cleanup_autochecks or always_cleanup_autochecks:
            do_cleanup_autochecks()
        done = True

    if not done and opt_cleanup_autochecks: # -u as standalone option
        do_cleanup_autochecks()
        done = True


    if done:
        output_profile()
        sys.exit(0)
    elif (len(args) == 0 and not opt_keepalive) or len(args) > 2:
        usage()
        sys.exit(1)
    elif opt_keepalive:
        do_check_keepalive()
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

        # honor --checks= also when checking (makes testing easier)
        if inventory_checks:
            check_types = inventory_checks.split(",")
        else:
            check_types = None

        do_check(hostname, ipaddress, check_types)

