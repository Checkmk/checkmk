#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# This file is also read in by check_mk's web pages. In that case,
# the variable check_mk_web is set to True

import os, sys, socket, time, getopt, glob, re, stat, py_compile, urllib

# These variable will be substituted at 'make dist' time
check_mk_version  = '(inofficial)'

# Some things have to be done before option parsing and might
# want to output some verbose messages.
if __name__ == "__main__":
    opt_verbose      = '-v' in sys.argv[1:] or '--verbose' in sys.argv[1:]
    opt_debug        = '--debug' in sys.argv[1:]
    opt_config_check = '-X' in sys.argv[1:] or '--config-check' in sys.argv[1:]
else:
    opt_verbose = False
    opt_debug = False
    opt_config_check = False

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
agents_dir                         = '/usr/share/check_mk/agents'
check_manpages_dir                 = '/usr/share/doc/check_mk/checks'
modules_dir                        = '/usr/share/check_mk/modules'
var_dir                            = '/var/lib/check_mk' 
autochecksdir                      = var_dir + '/autochecks'
snmpwalks_dir                      = var_dir + '/snmpwalks'
precompiled_hostchecks_dir         = var_dir + '/precompiled'
counters_directory                 = var_dir + '/counters'
tcp_cache_dir			   = var_dir + '/cache'
rrd_path                           = var_dir + '/rrd'
logwatch_dir                       = var_dir + '/logwatch'
nagios_objects_file                = var_dir + '/check_mk_objects.cfg'
nagios_command_pipe_path           = '/var/log/nagios/rw/nagios.cmd'
www_group                          = None # unset
nagios_startscript                 = '/etc/init.d/nagios'
nagios_binary                      = '/usr/sbin/nagios'
nagios_config_file                 = '/etc/nagios/nagios.cfg'
logwatch_notes_url                 = "/nagios/logwatch.php?host=%s&file=%s"

def verbose(t):
    if opt_verbose:
        sys.stderr.write(t)
        sys.stderr.flush()


# During setup a file called defaults is created in the modules
# directory.  In this file all directories are configured.  We need to
# read in this file first. It tells us where to look for our
# configuration file. In python argv[0] always contains the directory,
# even if the binary lies in the PATH and is called without
# '/'. This allows us to find our directory by taking everying up to
# the first '/'

# Allow to specify defaults file on command line (needed for OMD)
if len(sys.argv) >= 2 and sys.argv[1] == '--defaults':
    defaults_path = sys.argv[2]
    del sys.argv[1:3]
elif __name__ == "__main__":
    defaults_path = os.path.dirname(sys.argv[0]) + "/defaults"
    
if opt_debug:
    sys.stderr.write("Reading default settings from %s\n" % defaults_path)
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
NEGATE         = '@negate'       # negation in boolean lists

# Basic Settings
agent_port                         = 6556
tcp_connect_timeout                = 5.0
do_rrd_update			   = False
aggr_summary_hostname              = "%s-s"
agent_min_version                  = 0 # warn, if plugin has not at least version
check_max_cachefile_age            = 0 # per default do not use cache files when checking
cluster_max_cachefile_age          = 90   # secs.
simulation_mode                    = False
perfdata_format                    = "standard" # also possible: "pnp"
debug_log                          = None

# SNMP communities
snmp_default_community             = 'public'
snmp_communities                   = {}

# Inventory and inventory checks
inventory_check_interval           = None # Nagios intervals (4h = 240)
inventory_check_severity           = 2    # critical
inventory_max_cachefile_age        = 120  # secs.

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
nagios_illegal_chars               = '`~!$%^&*|\'"<>?,()='

# Settings for web pages (THIS IS DEPRECATED AND POINTLESS AND WILL BE REMOVED ANY DECADE NOW)
multiadmin_users                     = None # means: all
multiadmin_action_users              = None # means: all
multiadmin_sites                     = { "" : {} }
multiadmin_restrict                  = False
multiadmin_restrict_actions          = False
multiadmin_unrestricted_users        = []
multiadmin_unrestricted_action_users = []
multiadmin_sounds                    = {}
multiadmin_use_siteicons             = False
multiadmin_debug                     = False
multiadmin_sidebar                   = [('admin', 'open'), ('tactical_overview', 'open'), ('sitestatus', 'open'), \
					('search', 'open'), ('views', 'open'), ('hostgroups', 'closed'), \
					('servicegroups', 'closed'), ('hosts', 'closed'), ('time', 'open'), \
					('nagios_legacy', 'closed'), ('performance', 'closed'), ('master_control', 'closed'), ('about', 'closed')]

# Data to be defined in main.mk
checks                               = []
all_hosts                            = []
snmp_hosts                           = [ (['snmp'], ALL_HOSTS) ]
bulkwalk_hosts                       = None
non_bulkwalk_hosts                   = None
ignored_checktypes                   = [] # exclude from inventory
ignored_services                     = [] # exclude from inventory
host_groups                          = []
service_groups                       = []
service_contactgroups                = []
service_notification_periods         = []
host_notification_periods            = []
host_contactgroups                   = []
parents                              = []
define_timeperiods                   = {}
define_hostgroups                    = None
define_servicegroups                 = None
define_contactgroups                 = None
clusters                             = {}
clustered_services                   = []
clustered_services_of                = {} # new in 1.1.4
datasource_programs                  = []
service_aggregations                 = []
service_dependencies                 = []
non_aggregated_hosts                 = []
aggregate_check_mk                   = False
aggregation_output_format            = "single" # new in 1.1.6. Possible also: "multiline"
summary_host_groups                  = []
summary_service_groups               = [] # service groups for aggregated services
summary_service_contactgroups        = [] # service contact groups for aggregated services
summary_host_notification_periods    = []
summary_service_notification_periods = []
ipaddresses                          = {} # mapping from hostname to ipadress
only_hosts                           = None
extra_host_conf                      = {}
extra_summary_host_conf              = {}
extra_service_conf                   = {}
extra_nagios_conf                    = ""
service_descriptions                 = {}
donation_hosts                       = []
donation_command                     = 'mail -r checkmk@yoursite.de  -s "Host donation %s" donatehosts@mathias-kettner.de' % check_mk_version

# Settings for filesystem checks (df, df_vms, df_netapp and maybe others)
filesystem_default_levels          = (80, 90)
filesystem_levels                  = []
df_magicnumber_normsize            = 20 # Standard size if 20 GB
df_lowest_warning_level            = 50 # Never move warn level below 50% due to magic factor
df_lowest_critical_level           = 60 # Never move crit level below 60% due to magic factor

# This is obsolete stuff and should be moved to the check plugins some day
inventory_df_exclude_fs            = [ 'nfs', 'smbfs', 'cifs', 'iso9660' ]
inventory_df_exclude_mountpoints   = [ '/dev' ]
inventory_df_check_params          = 'filesystem_default_levels'


# The following data structures will be filled by the various checks
# found in the checks/ directory.
check_info                         = {} # all known checks
precompile_params                  = {} # optional functions for parameter precompilation, look at df for an example
check_config_variables             = [] # variables (names) in checks/* needed for check itself
snmp_info                          = {} # whichs OIDs to fetch for which check (for tabular information)
snmp_info_single                   = {} # similar, but for single SNMP variables (MIB-Name BASE-OID List-of-Suffixes)
snmp_scan_functions                = {} # SNMP autodetection


# Now include the other modules. They contain everything that is needed
# at check time (and many of that is also needed at administration time).
try:
    for module in [ 'check_mk_base', 'snmp' ]:
        filename = modules_dir + "/" + module + ".py"
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

def lookup_filesystem_levels(host, mountpoint):
    levels = service_extra_conf(host, mountpoint, filesystem_levels)
    # may return 0, 1 or more answers
    if len(levels) == 0:
        return filesystem_default_levels
    else:
        return levels[0]

def precompile_filesystem_levels(host, item, params):
    if  params is filesystem_default_levels:
        params = lookup_filesystem_levels(host, item)
    return params


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
    for f in glob.glob(checks_dir + "/*"):
        if not f.endswith("~"): # ignore emacs-like backup files
            try:
                execfile(f)
            except Exception, e:
                sys.stderr.write("Error in plugin file %s: %s\n" % (f, e))
                if opt_debug:
                    raise
                sys.exit(5)
   

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
    return set([ name for name,value in globals().items() if name[0] != '_' and type(value) != type(lambda:0) ])

if opt_config_check:
    vars_before_config = all_nonfunction_vars()


list_of_files = [ check_mk_configfile ] + glob.glob(check_mk_configdir + '/*.mk')
final_mk = check_mk_basedir + "/final.mk"
if os.path.exists(final_mk):
    list_of_files.append(final_mk)
for f in list_of_files:
    try:
        if opt_debug:
            sys.stderr.write("Reading config file %s...\n" % f)
        execfile(f)
    except Exception, e:
        sys.stderr.write("Cannot read in configuration file %s:\n%s\n" % (f, e))
        if __name__ == "__main__":
            sys.exit(3)
        else:
            raise

       
# Load python-rrd if available and not switched off.
if do_rrd_update:
    try:
        import rrdtool
    except:
        sys.stdout.write("ERROR: Cannot do direct rrd updates since the Python module\n"+
                         "'rrdtool' could not be loaded. Please install python-rrdtool\n"+
                         "or set do_rrd_update to False in main.mk.\n")
        sys.exit(3)

# read automatically generated checks. They are prepended to the check
# table: explicit user defined checks override automatically generated
# ones. Do not read in autochecks, if check_mk is called as module.
autochecks = []
if __name__ == "__main__":
    for f in glob.glob(autochecksdir + '/*.mk'):
        try:
           autochecks += eval(file(f).read())
        except SyntaxError,e:
           sys.stderr.write("Syntax error in file %s: %s\n" % (f, e))
           sys.exit(3)
        except Exception, e:
           sys.stderr.write("Error in file %s:\n%s\n" % (f, e))
           sys.exit(3)
        
checks = autochecks + checks

if opt_config_check:
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'rrdtool', 'final_mk', 'list_of_files', 'autochecks'])
    errors = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            sys.stderr.write("Invalid configuration variable '%s'\n" % name)
            errors += 1
    if errors > 0:
        sys.stderr.write("--> Found %d invalid variables\n" % errors)
        sys.stderr.write("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)


# Convert www_group into numeric id
if type(www_group) == str:
    try:
        import grp
        www_group = grp.getgrnam(www_group)[2]
    except Exception, e:
        sys.stderr.write("Cannot convert group '%s' into group id: %s\n" % (www_group, e))
        sys.stderr.write("Please set www_group to an existing group in main.mk.\n")
        sys.exit(3)

# --------------------------------------------------------------------------
# FINISHED WITH READING IN USER DATA
# Now we are finished with reading in user data and can safely define
# further functions and variables without fear of name clashes with user
# defined variables.
# --------------------------------------------------------------------------

#   +----------------------------------------------------------------------+
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def have_perfdata(checkname):
    return check_info[checkname][2]

def output_check_info():
   print "Available check types:"
   print
   print "                      plugin   perf-  in- "
   print "Name                  type     data   vent.  service description"
   print "-------------------------------------------------------------------------"

   checks_sorted = check_info.items()
   checks_sorted.sort()
   for check_type, info in checks_sorted:
      try:
         func, itemstring, have_perfdata, invfunc = info
         if have_perfdata == 1:
            p = tty_green + tty_bold + "yes" + tty_normal
         else:
            p = "no"
         if invfunc == no_inventory_possible:
            i = "no"
         else:
            i = tty_blue + tty_bold + "yes" + tty_normal
            
         if check_uses_snmp(check_type):
             typename = tty_magenta + "snmp" + tty_normal
         else:
             typename = tty_yellow + "tcp " + tty_normal
             
         print (tty_bold + "%-19s" + tty_normal + "   %s     %-3s    %-3s    %s") % \
               (check_type, typename, p, i, itemstring)
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
def hosttags_match_taglist(hosttags, required_tags):
    for tag in required_tags:
        if len(tag) > 0 and tag[0] == '!':
            negate = True
            tag = tag[1:]
        else:
            negate = False
        if (tag in hosttags) == negate:
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
    
    # host might by explicitely configured as not aggregated
    if in_binary_hostlist(hostname, non_aggregated_hosts):
        return False

    # convert into host_conf_list suitable for host_extra_conf()
    host_conf_list = [ entry[:-1] for entry in service_aggregations ]  
    is_aggr = len(host_extra_conf(hostname, host_conf_list)) > 0
    return is_aggr

# Determines the aggretated service name for a given
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
def get_snmp_community(hostname):
    # Keep up old behaviour for a while...
    if type(snmp_communities) == dict:
        for com, hostlist in snmp_communities.items():
            if hostname in strip_tags(hostlist):
                return com

    else:
        communities = host_extra_conf(hostname, snmp_communities)
        if len(communities) > 0:
            return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community


def check_uses_snmp(check_type):
    check_name = check_type.split(".")[0]
    return snmp_info.has_key(check_name) or snmp_info_single.has_key(check_name)

def is_snmp_host(hostname):
    return in_binary_hostlist(hostname, snmp_hosts)

def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return in_binary_hostlist(hostname, bulkwalk_hosts)
    elif non_bulkwalk_hosts:
        return not in_binary_hostlist(hostname, non_bulkwalk_hosts)
    else:
        return False

def get_single_oid(hostname, ipaddress, oid):
    global g_single_oid_hostname
    global g_single_oid_cache

    if g_single_oid_hostname != hostname:
        g_single_oid_hostname = hostname
        g_single_oid_cache = {}

    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    community = get_snmp_community(hostname)
    if is_bulkwalk_host(hostname):
        command = "snmpget -v2c"
    else:
        command = "snmpget -v1" 
    command += " -On -OQ -Oe -c %s %s %s 2>/dev/null" % (community, ipaddress, oid)
    try:
	if opt_verbose:
	    sys.stdout.write("Running '%s'\n" % command)
	    
        snmp_process = os.popen(command, "r")
	line = snmp_process.readline().strip()
	item, value = line.split("=")
	value = value.strip()
	if opt_verbose:
	   sys.stdout.write("SNMP answer: ==> [%s]\n" % value)
	
	
        # try to remove text, only keep number
        # value_num = value_text.split(" ")[0]
        # value_num = value_num.lstrip("+")
        # value_num = value_num.rstrip("%")
	# value = value_num
    except:
        value = None

    g_single_oid_cache[oid] = value
    return value

def snmp_scan(hostname, ipaddress):
    sys.stdout.write("Scanning host %s(%s)..." % (hostname, ipaddress))
    sys_descr = get_single_oid(hostname, ipaddress, ".1.3.6.1.2.1.1.1.0")
    if sys_descr == None:
	print "no SNMP answer"
	return []

    found = []
    for checktype, detect_function in snmp_scan_functions.items():
        try:
            if detect_function(lambda oid: get_single_oid(hostname, ipaddress, oid)):
                found.append(checktype)
	        sys.stdout.write("%s " % checktype)
	        sys.stdout.flush()
        except:
	    pass
    if found == []:
	sys.stdout.write("nothing detected.\n")
    else:
	sys.stdout.write("\n")
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

# If host is node of a cluster, return name of that cluster
# (untagged). If not, return None. If a host belongt to
# more than one cluster, then a random cluster is choosen.
def cluster_of(hostname):
    for clustername, nodes in clusters.items():
        if hostname in nodes:
            return strip_tags(clustername)
    return None

# Determine wether a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    # 1. New style: explicitlely assigned services
    for cluster, conf in clustered_services_of.items():
        if hostname in nodes_of(cluster) and \
            in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
        cluster = cluster_of(hostname)
        if cluster:
            return cluster
    
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
g_check_table_cache = {}
def get_check_table(hostname):
    # speed up multiple lookup of same host
    if hostname in g_check_table_cache:
        return g_check_table_cache[hostname]

    check_table = {}
    for entry in checks:
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
                continue # optimize most common case: hostname mismatch
            hostlist = [ strip_tags(hostlist) ]
        elif type(hostlist[0]) == str:
            hostlist = strip_tags(hostlist)
        elif hostlist != []:
            raise MKGeneralException("Invalid entry '%r' in check table. Must be single hostname or list of hostnames" % hostinfolist)

        if hosttags_match_taglist(tags_of_host(hostname), tags) and \
               in_extraconf_hostlist(hostlist, hostname):
            descr = service_description(checkname, item)
            deps  = service_deps(hostname, descr)
            check_table[(checkname, item)] = (params, descr, deps)

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
def get_datasource_program(hostname, ipaddress):
    programs = host_extra_conf(hostname, datasource_programs)
    if len(programs) == 0:
        return None
    else:
        return programs[0].replace("<IP>", ipaddress).replace("<HOST>", hostname)
    

def service_description(checkname, item):
    if checkname not in check_info:
        raise MKGeneralException("Unknown check type '%s'.\n"
                                 "Please use check_mk -L for a list of all check types.\n" % checkname)

    # use user-supplied service description, of available
    descr_format = service_descriptions.get(checkname)
    if not descr_format:
        descr_format = check_info[checkname][1]

    if type(item) == str:
        # Remove characters from item name that are banned by Nagios
        item_safe = "".join([ c for c in item if c not in nagios_illegal_chars ])
	if "%s" not in descr_format:
	    descr_format += " %s"
        return descr_format % (item_safe,)
    if type(item) == int or type(item) == long:
        if "%s" not in descr_format:
	    descr_format += " %s" 
        return descr_format % (item,)
    else:
        return descr_format

#   +----------------------------------------------------------------------+
#   |    ____             __ _                     _               _       |
#   |   / ___|___  _ __  / _(_) __ _    ___  _   _| |_ _ __  _   _| |_     |
#   |  | |   / _ \| '_ \| |_| |/ _` |  / _ \| | | | __| '_ \| | | | __|    |
#   |  | |__| (_) | | | |  _| | (_| | | (_) | |_| | |_| |_) | |_| | |_     |
#   |   \____\___/|_| |_|_| |_|\__, |  \___/ \__,_|\__| .__/ \__,_|\__|    |
#   |                          |___/                  |_|                  |
#   +----------------------------------------------------------------------+

def output_conf_header(outfile):
    outfile.write("""#
# Automatically created by check_mk at %s
# Do not edit
#


""" % (time.asctime()))

def all_active_hosts():
    if only_hosts == None:
        return strip_tags(all_hosts)
    else:
        return [ hostname for hostname in strip_tags(all_hosts) \
                 if in_binary_hostlist(hostname, only_hosts) ]

def all_active_clusters():
    if only_hosts == None:
        return strip_tags(clusters.keys())
    else:
        return [ hostname for hostname in strip_tags(clusters.keys()) \
                 if in_binary_hostlist(hostname, only_hosts) ]

def hostgroups_of(hostname):
    return host_extra_conf(hostname, host_groups)
  
def summary_hostgroups_of(hostname):
    return host_extra_conf(hostname, summary_host_groups)

def host_contactgroups_of(hostlist):
    cgrs = []
    for host in hostlist:
        cgrs += host_extra_conf(host, host_contactgroups)
    return list(set(cgrs))

def host_contactgroups_nag(hostlist):
    cgrs = host_contactgroups_of(hostlist)
    if len(cgrs) > 0: 
        return "    contact_groups +" + ",".join(cgrs) + "\n"
    else:
        return ""

def parents_of(hostname):
    par = host_extra_conf(hostname, parents)
    return par

def extra_host_conf_of(hostname):
   return extra_conf_of(extra_host_conf, hostname, None)

def extra_summary_host_conf_of(hostname):
   return extra_conf_of(extra_summary_host_conf, hostname, None)

def extra_service_conf_of(hostname, description):
   return extra_conf_of(extra_service_conf, hostname, description)

def extra_conf_of(confdict, hostname, service):
   result = ""
   for key, conflist in confdict.items():
      if service:
	 values = service_extra_conf(hostname, service, conflist)
         format = "    %-24s %s\n"
      else:
	 values = host_extra_conf(hostname, conflist)
	 format = "    %-14s %s\n"
      if len(values) > 0:
	 result += format % (key, values[0])
   return result


# Return a list of services this services depends upon
def service_deps(hostname, servicedesc):
    deps = []
    for entry in service_dependencies:
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

def in_binary_hostlist(hostname, conf):
    # if we have just a list of strings just take it as list of (may be tagged) hostnames
    if len(conf) > 0 and type(conf[0]) == str:
        return hostname in strip_tags(conf)
    
    for entry in conf:
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


# Compute list of service_groups or contact_groups of service
# conf is either service_groups or service_contactgroups
def service_extra_conf(hostname, service, conf):
    entries = []
    for entry in conf:
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
        raise MKGeneralException('Invalid emtpy entry [ "" ] in configuration')

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


def output_timeperiods(outfile = sys.stdout):
    daynames = [ "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday" ]
    
    output_conf_header(outfile)
    for name, times in define_timeperiods.items():
        if len(times) != 7:
            raise MKGeneralException("Timeperiod definition '%s' needs 7 time ranges, but has %d" % (name, len(times)))
        outfile.write("define timeperiod {\n"
                      "  timeperiod_name   %s\n"
                      "  alias             %s\n" % (name, name))
        for day, period in zip(daynames, times):
            if period: # None -> no time
                outfile.write("  %-16s  %s\n" % (day, period))
        outfile.write("}\n\n")
        

# We deal with four kinds of hosts here
# 1. normal, physical hosts
# 2. summary hosts of normal hosts (for service aggregation)
# 3. cluster hosts - consisting of several physical hosts
# 4. summary cluster hosts
def output_hostconf(outfile = sys.stdout):
    need_default_host_group = False
    hostgroups_to_define = set([])
    output_conf_header(outfile)

    #   _ 
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    for hostname in all_hosts_untagged:
       try:
          if opt_verbose:
              sys.stderr.write("getting IP address of %s..." % hostname)
          ip = lookup_ipaddress(hostname)
          if opt_verbose:
              sys.stderr.write("%s\n" % ip)
       except:
	  raise MKGeneralException("Cannot determine ip address of %s. Please add to ipaddresses." % hostname)

       hgs = hostgroups_of(hostname)
       hostgroups = ",".join(hgs)
       if hostgroups == "":
          hostgroups = default_host_group
          need_default_host_group = True
       elif define_hostgroups:
          hostgroups_to_define.update(hgs)
       
       nottimes = host_extra_conf(hostname, host_notification_periods)
       if len(nottimes) > 0:
           nottime = "    notification_period      " + nottimes[0] + "\n"
       else:
           nottime = ""

       parents_list = parents_of(hostname)
       if len(parents_list) > 0:
           parents_txt = "\n    parents        " + (",".join(parents_list))
       else:
           parents_txt = ""
      
       outfile.write("""define host {
    use            %s
    name           host_%s
    host_name      %s
    alias          %s%s
    host_groups    +%s
%s%s%s    address        %s
}

""" % (host_template, hostname, hostname, hostname, parents_txt,
       hostgroups, nottime, host_contactgroups_nag([hostname]), 
       extra_host_conf_of(hostname), ip))

       #   ____  
       #  |___ \ 
       #   __) | 
       #  / __/  
       #  |_____|  2. summary hosts of physical hosts

       # Does this host have aggregated services? --> Output definition for
       # Summary host
       if host_is_aggregated(hostname):
	   hgs = summary_hostgroups_of(hostname)
           hostgroups = ",".join(hgs)
           if hostgroups == "":
              hostgroups = default_host_group
              need_default_host_group = True
	   elif define_hostgroups:
	      hostgroups_to_define.update(hgs)

           nottimes = host_extra_conf(hostname, summary_host_notification_periods)
           if len(nottimes) > 0:
               nottime = "    notification_period      " + nottimes[0] + "\n"
           else:
               nottime = ""

           outfile.write("""define host {
    use            %s-summary
    name           host_%s
    host_name      %s
    __realname     %s
    alias          Summary of %s
    host_groups    +%s
    parents        %s
%s%s%s    address        %s
}

""" % (host_template, summary_hostname(hostname), summary_hostname(hostname), hostname, hostname,
       hostgroups, hostname, host_contactgroups_nag([hostname]), nottime, 
       extra_summary_host_conf_of(hostname), ip))
	   
    #   _____ 
    #  |___ / 
    #    |_ \ 
    #   ___) |
    #  |____/   3. Cluster hosts

    for clustername in all_active_clusters():
        nodes = nodes_of(clustername)
	for node in nodes:
	    if node not in all_hosts_untagged:
                raise MKGeneralException("Node %s of cluster %s not in all_hosts." % (node, clustername))
		
	hgs = hostgroups_of(clustername)
        hostgroups = ",".join(hgs)
        if hostgroups == "":
            hostgroups = default_host_group
            need_default_host_group = True
	elif define_hostgroups:
	    hostgroups_to_define.update(hgs)
	try:
	    node_ips = [ lookup_ipaddress(h) for h in nodes ]
	except:
	    node_ips = []

        outfile.write("""define host {
    use            %s
    name           host_%s
    host_name      %s
    alias          Cluster of %s
    host_groups    +%s
%s    address        0.0.0.0
%s    parents        %s
    _NODEIPS       %s
}

""" % (cluster_template, clustername, clustername, ", ".join(nodes), hostgroups, 
       host_contactgroups_nag([clustername]), extra_host_conf_of(clustername),
       ",".join(nodes), " ".join(node_ips)))

        #   _  _   
        #  | || |  
        #  | || |_ 
        #  |__   _|
        #     |_|    4. summary hosts of cluster hosts

        # Does this cluster-host have aggregated services? --> Output definition for
        # Summary host
        if host_is_aggregated(clustername):
	   hgs = summary_hostgroups_of(clustername)
           hostgroups = ",".join(hgs)
           if hostgroups == "":
              hostgroups = default_host_group
              need_default_host_group = True
	   elif define_hostgroups:
	      hostgroups_to_define.update(hgs)

           outfile.write("""define host {
    use            %s-summary
    name           host_%s
    host_name      %s
    __realname     %s
    alias          Summary of Cluster of %s
    host_groups    +%s
%s%s    address        0.0.0.0
    parents        %s
    _NODEIPS       %s
}
""" % (cluster_template, summary_hostname(clustername), summary_hostname(clustername),
       clustername, ", ".join(nodes), hostgroups, 
           host_contactgroups_nag([clustername]), 
	   extra_summary_host_conf_of(clustername),
	   clustername, " ".join(node_ips)))

    # output default hostgroup in order to be consistant
    if need_default_host_group:
       outfile.write("""# default hostgroup
define hostgroup {
    hostgroup_name %s
    alias          Fallback hostgroup of check_mk
}

""" % default_host_group)
    
    # define hostgroups, if user wants to
    if define_hostgroups:
       hgs = list(hostgroups_to_define)
       hgs.sort()
       for hg in hgs:
	  try:
             alias = define_hostgroups[hg]
          except:
             alias = hg
          outfile.write("""
define hostgroup {
    hostgroup_name %s
    alias          %s
}
""" % (hg, alias))

    

def output_serviceconf(outfile = sys.stdout):
    output_conf_header(outfile)

    # Keep list of all check_mk-% check names. We need to define
    # these as dummy commands. This enables us to have different
    # specific check names for tools like PNP4Nagios, which assign
    # templates according to the check names
    checknames = set([])

    servicegroups_to_output = set([])

    outfile.write("# Service checks generated by check_mk\n\n")
    clusters_hostdefs = all_active_clusters()
    for hostname in all_hosts_untagged + clusters_hostdefs:

        outfile.write("# ----------------------------------------------------\n")
        outfile.write("# %s\n" % hostname)
        outfile.write("# ----------------------------------------------------\n")

        host_checks = get_check_table(hostname).items()
        aggregated_services_conf = set([])
        do_aggregation = host_is_aggregated(hostname)
        have_at_least_one_service = False
        for ((checkname, item), (params, description, deps)) in host_checks:
            if have_perfdata(checkname):
                template = passive_service_template_perf
            else:
                template = passive_service_template
        
            sergr = service_extra_conf(hostname, description, service_groups)
            if len(sergr) > 0:
                sg = "    service_groups           +" + ",".join(sergr) + "\n"
                if define_servicegroups:
	           servicegroups_to_output.update(sergr)
            else:
                sg = ""
                
            sercgr = service_extra_conf(hostname, description, service_contactgroups)
	    contactgroups_to_output.update(sercgr)
            if len(sercgr) > 0:
                scg = "    contact_groups           +" + ",".join(sercgr) + "\n"
            else:
                scg = ""

            nottimes = service_extra_conf(hostname, description, service_notification_periods)
            if len(nottimes) > 0:
                nottime = "    notification_period      " + nottimes[0] + "\n"
            else:
                nottime = ""
            
            # Hardcoded for logwatch check: Link to logwatch.php
            if checkname == "logwatch":
                logwatch = "    notes_url                " + (logwatch_notes_url % (urllib.quote(hostname), urllib.quote(item))) + "\n"
            else:
                logwatch = "";

            # Services Dependencies
            for dep in deps:
                outfile.write("define servicedependency {\n"
                             "    use                           %s\n"
                             "    host_name                     %s\n"
                             "    service_description           %s\n"
                             "    dependent_host_name           %s\n"
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

	    outfile.write("""define service {
    use                      %s
    host_name                %s
    service_description      %s
%s%s%s%s%s    check_command            check_mk-%s
}

""" % ( template, hostname, description, sg, scg, nottime, logwatch, 
   extra_service_conf_of(hostname, description),
   checkname ))
            checknames.add(checkname)
            have_at_least_one_service = True


        # Now create definitions of the aggregated services for this host
        if do_aggregation and service_aggregations:
            outfile.write("\n# Aggregated services of host %s\n\n" % hostname)

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
    use                      %s
%s    host_name                %s
}

""" % (pingonly_template, extra_service_conf_of(hostname, "PING"), summary_hostname(hostname)))

        for description in aggr_descripts:
            sergr = service_extra_conf(hostname, description, summary_service_groups)
            if len(sergr) > 0:
                sg = "    service_groups            +" + ",".join(sergr) + "\n"
		if define_servicegroups:
		   servicegroups_to_output.update(sergr)
            else:
                sg = ""
                
            sercgr = service_extra_conf(hostname, description, summary_service_contactgroups)
	    contactgroups_to_output.update(sercgr)
            if len(sercgr) > 0:
                scg = "    contact_groups            +" + ",".join(sercgr) + "\n"
            else:
                scg = ""

            nottimes = service_extra_conf(hostname, description, summary_service_notification_periods)
            if len(nottimes) > 0:
                nottime = "    notification_period       " + nottimes[0] + "\n"
            else:
                nottime = ""

            outfile.write("""define service {
    use                      %s
    host_name                %s
%s%s%s%s    service_description      %s
}

""" % ( summary_service_template, summary_hostname(hostname), sg, scg, nottime, 
   extra_service_conf_of(hostname, description), description  ))

        # Active check for check_mk
        if have_at_least_one_service:
            outfile.write("""
# Active checks of host %s

define service {
    use                      %s
    host_name                %s
%s    service_description      Check_MK
}

""" % (hostname, active_service_template, hostname, extra_service_conf_of(hostname, "Check_MK")))
            # Inventory checks - if user has configured them. Not for clusters.
            if inventory_check_interval and not is_cluster(hostname):
                outfile.write("""
define service {
    use                      %s
    host_name                %s
    normal_check_interval    %d
%s    service_description      Check_MK inventory
}

define servicedependency {
    use                      %s
    host_name                %s
    service_description      Check_MK
    dependent_host_name      %s
    dependent_service_description Check_MK inventory
}


""" % (inventory_check_template, hostname, inventory_check_interval,
       extra_service_conf_of(hostname, "Check_MK inventory"),
       service_dependency_template, hostname, hostname))
                
        else:
            outfile.write("""
define service {
    use                      %s
%s    host_name                %s
}

""" % (pingonly_template, extra_service_conf_of(hostname, "PING"), hostname))

    if generate_dummy_commands:
        outfile.write("# Dummy check commands for passive services\n\n")
        for checkname in checknames:
            outfile.write("""define command {
        command_name             check_mk-%s
        command_line             %s
    }

""" % ( checkname, dummy_check_commandline ))
    if define_servicegroups:
	 sgs = list(servicegroups_to_output)
	 sgs.sort()
	 for sg in sgs:
	    try:
	       alias = define_servicegroups[sg]
	    except:
	       alias = sg
	    outfile.write("""define servicegroup {
  servicegroup_name %s
  alias             %s
}

""" % (sg, alias))



def output_contactgroups(cgs, outfile = sys.stdout):
    cgs = list(cgs)
    cgs.sort()
    outfile.write("\n# Contact groups, (controlled by define_contactgroups)\n")
    for name in cgs:
	if type(define_contactgroups) == dict:
	    alias = define_contactgroups.get(name, name)
	else:
	    alias = name
        outfile.write("\ndefine contactgroup {\n"
		"  contactgroup_name %s\n"
		"  alias             %s\n"
		"}\n" % (name, alias))


#   +----------------------------------------------------------------------+
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+


def inventorable_checktypes(include_snmp = True):
    checknames = [ k for k in check_info.keys()
                   if check_info[k][3] != no_inventory_possible
                   and (k not in ignored_checktypes)
                   and (include_snmp or not check_uses_snmp(k)) ]
    checknames.sort()
    return checknames


def do_snmp_scan(hostnamelist):
    only_snmp_hosts = False
    if hostnamelist == []:
        hostnamelist = all_hosts_untagged
        only_snmp_hosts = True
    for hostname in hostnamelist:
        if only_snmp_hosts and not is_snmp_host(hostname):
	    if opt_verbose:
		sys.stdout.write("Skipping %s, not an snmp host\n" % hostname)
            continue
	try:
	     ipaddress = lookup_ipaddress(hostname)
	except:
	     print "Cannot resolve %s into IP address. Skipping." % hostname
	     continue
	checknames = snmp_scan(hostname, ipaddress)
	for checkname in checknames:
	    make_inventory(checkname, [hostname])
	

def make_inventory(checkname, hostnamelist, check_only=False):
    try:
        inventory_function = check_info[checkname][3]
    except KeyError:
        sys.stderr.write("No such check type '%s'. Try check_mk -I list.\n" % checkname)
        sys.exit(1)

    newchecks = []
    count_new = 0
    checked_hosts = []

    # if no hostnamelist is specified, we use all hosts
    if not hostnamelist or len(hostnamelist) == 0:
        global opt_use_cachefile
        opt_use_cachefile = True
        hostnamelist = all_hosts_untagged

    try:
       for host in hostnamelist:
          if opt_no_snmp_hosts and is_snmp_host(host):
              if opt_verbose:
                  print "%s is a SNMP-only host. Skipping." % host
              continue

          if is_cluster(host):
              print "%s is a cluster host and cannot be inventorized." % host
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
                     print "Cannot resolve %s into IP address. Skipping." % hostname
                     continue
             else:
                 ipaddress = None # not needed, not TCP used
            
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
              info = get_realhost_info(hostname, ipaddress, checkname_base, inventory_max_cachefile_age)
          except MKAgentError, e:
              if check_only:
                  raise
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
              inventory = inventory_function(checkname, info) # inventory is a list of pairs (item, current_value)
          except Exception, e:
              if opt_debug:
                  raise
              sys.stderr.write("%s: Invalid output from agent or invalid configuration: %s\n" % (hostname, e))
              continue

          for entry in inventory:
              if len(entry) == 2: # comment is now obsolete
                  item, paramstring = entry
              else:
                  item, comment, paramstring = entry

              description = service_description(checkname, item)

              # Find logical host this check belongs to. The service might belong to a cluster. 
              hn = host_of_clustered_service(hostname, description)
              
              # Now compare with already known checks for this host (from
              # previous inventory or explicit checks). Also drop services
              # the user wants to ignore via 'ignored_services'.
              checktable = get_check_table(hn)
              checked_items = [ i for ( (cn, i), (par, descr, deps) ) \
                                in checktable.items() if cn == checkname ]
              if item in checked_items:
                  continue # we have that already

              if service_ignored(hn, description):
                  continue # user does not want this item to be checked
              
              newcheck = '  ("%s", "%s", %r, %s),' % (hn, checkname, item, paramstring)
              newcheck += "\n"
              if newcheck not in newchecks: # avoid duplicates if inventory outputs item twice
                  newchecks.append(newcheck)
                  count_new += 1


    except KeyboardInterrupt:
        sys.stderr.write('<Interrupted>\n')

    if not check_only:
        if newchecks != []:
            filename = autochecksdir + "/" + checkname + "-" + time.strftime("%Y-%m-%d_%H.%M.%S")
	    while os.path.exists(filename + ".mk"): # more that one file a second..
		filename += ".x"
            filename += ".mk"
            if not os.path.exists(autochecksdir):
               os.makedirs(autochecksdir)
            file(filename, "w").write('# %s\n[\n%s]\n' % (filename, ''.join(newchecks)))
	    sys.stdout.write('%-30s ' % (tty_blue + checkname + tty_normal))
            sys.stdout.write('%s%d new checks%s\n' % (tty_bold + tty_green, count_new, tty_normal))
    else:
        return count_new


def check_inventory(hostname):
    newchecks = []
    total_count = 0
    only_snmp = is_snmp_host(hostname)
    check_table = get_check_table(hostname)
    hosts_checktypes = set([ ct for (ct, item), params in check_table.items() ])
    try:
        for ct in inventorable_checktypes():
            if only_snmp and not check_uses_snmp(ct):
                continue # No TCP checks on SNMP-only hosts
            elif check_uses_snmp(ct) and ct not in hosts_checktypes:
                continue
            count = make_inventory(ct, [hostname], True)
            if count > 0:
                newchecks.append((ct, count))
                total_count += count
        if total_count > 0:
            info = ", ".join([ "%s:%d" % (ct, count) for ct,count in newchecks ])
            statustext = { 0 : "OK", 1: "WARNING", 2:"CRITICAL" }.get(inventory_check_severity, "UNKNOWN")
            sys.stdout.write("%s - %d unchecked services (%s)\n" % (statustext, total_count, info))
            sys.exit(inventory_check_severity)
        else:
            sys.stdout.write("OK - no unchecked services found\n")
            sys.exit(0)
    except SystemExit, e:
            raise e
    except Exception, e:
        sys.stdout.write("UNKNOWN - %s\n" % (e,))
        sys.exit(3)


def service_ignored(hostname, service_description):
    return in_boolean_serviceconf_list(hostname, service_description, ignored_services)

def in_boolean_serviceconf_list(hostname, service_description, conflist):
    for entry in conflist:
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

#   +----------------------------------------------------------------------+
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+

def find_check_plugin(checktype):
   filename = checks_dir + "/" + checktype
   if os.path.exists(filename):
      return filename

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
         sys.stderr.write("Error precompiling checks for host %s: %s\n" % (host, e))
         sys.exit(5)

# read python file and strip comments
def stripped_python_file(filename):
    a = ""
    for line in file(filename):
        l = line.strip()
        if l == "" or l[0] != '#':
            a += line # not stripped line because of indentation!
    return a

def precompile_hostcheck(hostname):
    if opt_verbose:
        sys.stderr.write("%s%s%-16s%s:" % (tty_bold, tty_blue, hostname, tty_normal))
   
    try:
        os.remove(compiled_filename)
        os.remove(source_filename)
    except:
        pass

    compiled_filename = precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    output = file(source_filename, "w")
    output.write("#!/usr/bin/python\n")
    output.write(stripped_python_file(modules_dir + "/check_mk_base.py"))

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v is supported
opt_verbose = '-v' in sys.argv
opt_debug   = False

# make sure these names are defined (even if never needed)
no_inventory_possible = None
precompile_filesystem_levels = None
filesystem_default_levels = None
""")

    # Compile in all neccessary global variables
    output.write("\n# Global variables\n")
    for var in [ 'check_mk_version', 'agent_port', 'tcp_connect_timeout', 'agent_min_version',
                 'perfdata_format', 'aggregation_output_format',
                 'aggr_summary_hostname', 'nagios_command_pipe_path',
                 'var_dir', 'counters_directory', 'tcp_cache_dir',
                 'check_mk_basedir', 'df_magicnumber_normsize', 
		 'df_lowest_warning_level', 'df_lowest_critical_level', 'nagios_user',
                 'www_group', 'cluster_max_cachefile_age', 'check_max_cachefile_age',
                 'simulation_mode', 'aggregate_check_mk', 'debug_log',
                 ]:
        output.write("%s = %r\n" % (var, globals()[var]))

    # check table, enriched with addition precompiled information.
    check_table = get_precompiled_check_table(hostname)
    output.write("\n# Checks for %s\n\n" % hostname)
    output.write("def get_sorted_check_table(hostname):\n    return %r\n\n" % check_table)

    # Do we need to load the SNMP module? This is the case, if the host
    # has at least one SNMP based check. Also collect the needed check
    # types.
    need_snmp_module = False
    needed_types = set([])
    for checktype, item, param, descr, aggr in check_table:
        needed_types.add(checktype.split(".")[0])
        if check_uses_snmp(checktype):
            need_snmp_module = True

    if need_snmp_module:
        output.write(stripped_python_file(modules_dir + "/snmp.py"))

    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table
    filenames = set([])
    for checktype in needed_types:
        path = find_check_plugin(checktype)
        if not path:
            raise MKGeneralException("Cannot find plugin for check type %s (missing file %s/%s)\n" % \
                                     (checktype, checks_dir, checktype))
        filenames.add(path)

    output.write("check_info = {}\n" +
                 "precompile_params = {}\n" +
                 "check_config_variables = []\n" +
                 "snmp_info = {}\n" +
		 "snmp_info_single = {}\n" +
		 "snmp_scan_functions = {}\n")

    
    for filename in filenames:
       output.write("# %s\n" % filename)
       output.write(stripped_python_file(filename))
       output.write("\n\n")
       if opt_verbose:
          sys.stderr.write(" %s%s%s" % (tty_green, filename.split('/')[-1], tty_normal))

    # direct update of RRD databases by check_mk
    if do_rrd_update:
        output.write("do_rrd_update = True\n" +
                     "import rrdtool\n" +
                     "rrd_path = %r\n" % rrd_path)
    else:
        output.write("do_rrd_update = False\n")

    # handling of clusters
    if is_cluster(hostname):
       output.write("clusters = { %r : %r }\n" %
                    (hostname, nodes_of(hostname)))
       output.write("def is_cluster(hostname):\n    return True\n\n")
    else:
       output.write("clusters = {}\ndef is_cluster(hostname):\n    return False\n\n")

    # snmp hosts
    output.write("def is_snmp_host(hostname):\n   return %r\n\n" % is_snmp_host(hostname))
    output.write("def is_bulkwalk_host(hostname):\n   return %r\n\n" % is_bulkwalk_host(hostname))

    # IP addresses
    needed_ipaddresses = {}
    nodes = []
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            ipa = lookup_ipaddress(node)
            needed_ipaddresses[node] = ipa
            nodes.append( (node, ipa) )
        ipaddress = None
    else:
        ipaddress = lookup_ipaddress(hostname) # might throw exception
        needed_ipaddresses[hostname] = ipaddress
        nodes = [ (hostname, ipaddress) ]
   
    output.write("ipaddresses = %r\n\n" % needed_ipaddresses)

    # datasource programs. Is this host relevant?
    # ACHTUNG: HIER GIBT ES BEI CLUSTERN EIN PROBLEM!! WIR MUESSEN DIE NODES
    # NEHMEN!!!!!

    dsprogs = {}
    for node, ipa in nodes:
        program = get_datasource_program(node, ipa)
        dsprogs[node] = program
    output.write("def get_datasource_program(hostname, ipaddress):\n" +
                 "    return %r[hostname]\n\n" % dsprogs)

    # SNMP community (might not be needed, but does never harm)
    snmp_comm = get_snmp_community(hostname)
    output.write("def get_snmp_community(hostname):\n    return %r\n\n" % snmp_comm)

    # aggregation
    output.write("def host_is_aggregated(hostname):\n    return %r\n\n" % host_is_aggregated(hostname))

    # Parameters for checks: Default values are defined in checks/*. The 
    # variables might be overridden by the user in main.mk. We need
    # to set the actual values of those variables here. Otherwise the users'
    # settings would get lost. But we only need to set those variables that
    # influence the check itself - not those needed during inventory.
    for var in check_config_variables:
        output.write("%s = %r\n" % (var, eval(var)))

    # perform actual check
    output.write("do_check(%r, %r)\n" % (hostname, ipaddress))
    output.close()

    # compile python
    py_compile.compile(source_filename, compiled_filename, compiled_filename, True)
    os.chmod(compiled_filename, 0755)

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

opt_nowiki = False

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


def list_all_manuals():
    table = []
    for filename in os.listdir(check_manpages_dir):
        if filename.endswith("~"):
            continue
        try:
            for line in file(check_manpages_dir + "/" + filename):
                if line.startswith("title:"):
                    table.append((filename, line.split(":", 1)[1].strip()))
        except:
            pass
    
    table.sort()
    print_table(['Check type', 'Title'], [tty_blue, tty_cyan], table)

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
    parameters_color = tty(6,4)
    examples_color = tty(6,4,1)

    filename = check_manpages_dir + "/" + checkname
    try:
        f = file(filename)
    except:
        print "No manpage for %s. Sorry." % checkname
        return

    sections = {}
    current_section = []
    current_variable = None
    sections['header'] = current_section
    lineno = 0
    empty_line_count = 0

    try:
        for line in f:
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
        print current_section
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
            return line.replace("{", "<b>").replace("}", "</b>")

        def print_sectionheader(line, ignored):
            print "H1:" + line

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
            print "<tr><td class=tt>%s</td><td>%s</td><td>%s</td></tr>" % (name, typ, text)

    else:
        def markup(line, attr):
            return line.replace("{", bold_color).replace("}", tty_normal + attr)
        
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
            netto = word.replace("{", "").replace("}", "")
            netto = re.sub("\033[^m]+m", "", netto)
            return len(netto)

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
                if s/x < need_spaces / spaces:
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
                        wrapped.append("")
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
        print_splitline(header_color_left, "Author:            ", header_color_right, header['author'])
        print_splitline(header_color_left, "License:           ", header_color_right, header['license'])
        distro = header['distribution']
        if distro == 'check_mk':
            distro = "official part of check_mk"
        print_splitline(header_color_left, "Distribution:      ", header_color_right, distro)
        ags = []
        for agent in header['agents'].split(","):
            agent = agent.strip()
            ags.append({ "vms" : "VMS", "linux":"Linux", "aix": "AIX", "solaris":"Solaris", "windows":"Windows", "snmp":"SNMP"}.get(agent, agent.upper()))
        print_splitline(header_color_left, "Supported Agents:  ", header_color_right, ", ".join(ags))
        if checkname in snmp_info_single:
            print_splitline(header_color_left, "Required MIB:      ", header_color_right, snmp_info_single[checkname][0])
        
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
    
    for name, path, canonical_name, descr, is_dir, owned_by_nagios, group_www in backup_paths:
        absdir = os.path.abspath(path)
        if is_dir:
            basedir = absdir
            filename = "."
            if os.path.exists(absdir):
                if opt_verbose:
                    sys.stderr.write("  Deleting old contents of '%s'\n" % absdir)
                shutil.rmtree(absdir)
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
	    sys.stdout.write(tty_blue + " counters")
	    sys.stdout.flush()
            flushed = True
	except:
	    pass

	# cache files
	d = 0
	dir = tcp_cache_dir
	for f in os.listdir(dir):
	    if f == host or f.startswith(host + "."):
		try:
		    os.remove(dir + "/" + f)
		    d += 1
                    flushed = True
		except:
		    pass
	if d == 1:
	    sys.stdout.write(tty_green + " cache")
	elif d > 1:
	    sys.stdout.write(tty_green + " cache(%d)" % d)
	sys.stdout.flush()

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
		sys.stdout.write(tty_magenta + " logfiles(%d)" % d)
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
    community = get_snmp_community(hostname)
    ip = lookup_ipaddress(hostname)
    if is_bulkwalk_host(hostname):
        cmd = "snmpbulkwalk -v2c"
    else:
        cmd = "snmpwalk -v1"
    cmd += " -Ob -OQ -c '%s' %s " % (community, ip)
    out = file(filename, "w")
    for oid in [ "", "enterprises" ]:
        oids = []
        values = []
        if opt_verbose:
            sys.stdout.write("%s..." % (cmd + oid))
            sys.stdout.flush()
        count = 0
        f = os.popen(cmd + oid)
        while True:
            line = f.readline()
            if not line:
                break
            parts = line.strip().split("=", 1)
            if len(parts) != 2:
                continue
            oid, value = parts
            if value.startswith('"'):
                while value[-1] != '"':
                    value += f.readline().strip()

            oids.append(oid)
            values.append(value)
        numoids = snmptranslate(oids)
        for numoid, value in zip(numoids, values):
            out.write("%s %s\n" % (numoid, value.strip()))
            count += 1
        if opt_verbose:
            sys.stdout.write("%d variables.\n" % count)
        
    out.close()
    if opt_verbose:
        sys.stdout.write("Successfully Wrote %s%s%s.\n" % (tty_bold, filename, tty_normal))

def show_paths():
    inst = 1
    conf = 2 
    data = 3
    pipe = 4
    dir = 1
    fil = 2

    paths = [
	( modules_dir,                 dir, inst, "Main components of check_mk"),
	( checks_dir,                  dir, inst, "Checks"),
        ( agents_dir,                  dir, inst, "Agents for operating systems"),
        ( doc_dir,                     dir, inst, "Documentatoin files"),
	( web_dir,                     dir, inst, "Check_MK's web pages"),
	( check_manpages_dir,          dir, inst, "Check manpages (for check_mk -M)"),
	( lib_dir,                     dir, inst, "Binary plugins (architecture specific)"),
        ( pnp_templates_dir,           dir, inst, "Templates for PNP4Nagios"),
	( nagios_startscript,          fil, inst, "Startscript for Nagios daemon"),
	( nagios_binary,               fil, inst, "Path to Nagios executable"),

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
	( rrd_path,                    dir, data, "Base directory of round robin databases"),
	( nagios_status_file,          fil, data, "Path to Nagios status.dat"),
	
	( nagios_command_pipe_path,    fil, pipe, "Nagios command pipe"),
	( livestatus_unix_socket,      fil, pipe, "Socket of Check_MK's livestatus module"),
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
    else:
        color = tty_bgblue
        add_txt = ""
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
    notperiod = (host_extra_conf(hostname, host_notification_periods) + [""])[0]
    print tty_yellow + "Notification:           " + tty_normal + notperiod
    agenttype = "TCP (port: %d)" % agent_port
    if is_snmp_host(hostname):
        community = get_snmp_community(hostname)
        if is_bulkwalk_host(hostname):
            bulk = "yes"
        else:
            bulk = "no"
        agenttype = "SNMP (community: '%s', bulk walk: %s)" % (community, bulk)
    print tty_yellow + "Type of agent:          " + tty_normal + agenttype
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
    # check_items.sort()
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
        ",".join(service_extra_conf(hostname, description, service_groups)),
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
 check_mk [-n] [-v] [-p] HOST [IPADDRESS]  check all services on HOST
 check_mk -I alltcp [HOST1 HOST2...]       inventory - find new services
 check_mk -S|-H|--timeperiods              output Nagios configuration files
 check_mk -C, --compile                    precompile host checks
 check_mk -U, --update                     precompile + create Nagios config
 check_mk -R, --restart                    precompile + config + Nagios restart
 check_mk -D, --dump [H1 H2 ..]            dump all or some hosts
 check_mk -d HOSTNAME|IPADDRESS            show raw information from agent
 check_mk --check-inventory HOSTNAME       check for items not yet checked
 check_mk --list-hosts [G1 G2 ...]         print list of hosts
 check_mk --list-tag TAG1 TAG2 ...         list hosts having certain tags
 check_mk -L, --list-checks                list all available check types
 check_mk -M, --man [CHECKTYPE]            show manpage for check CHECKTYPE
 check_mk --paths                          list all pathnames and directories
 check_mk -X, --check-config               check configuration for invalid vars
 check_mk --backup BACKUPFILE.tar.gz       make backup of configuration and data
 check_mk --restore BACKUPFILE.tar.gz      restore configuration and data
 check_mk --flush [HOST1 HOST2...]         flush all data of some or all hosts
 check_mk --donate                         Email data of configured hosts to MK
 check_mk --snmpwalk HOST1 HOST2 ...       Do snmpwalk on host
 check_mk -P, --package COMMAND            do package operations
 check_mk -V, --version                    print version
 check_mk -h, --help                       print this help

OPTIONS:
  -v             show what's going on
  -p             also show performance data (use with -v)
  -n             do not submit results to Nagios, do not save counters
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

NOTES:
  -I can be restricted to certain check types. Write '-I df' if you
  just want to look for new filesystems. Use 'check_mk -L' for a list
  of all check types. SNMP base checks must always named explicitely.

  -H, -S and --timeperiods output Nagios configuration data for hosts,
  services and timeperiods resp. to stdout. Two or more of them can
  be used at once.

  -U redirects both the output of -S, -H and --timeperiods to the file
  %s and also calls check_mk -C.

  -D, --dump dumps out the complete configuration and information
  about one, several or all hosts. It shows all services, hostgroups,
  contacts and other information about that host. 

  -d does not work not clusters (such defined in main.mk) but only on
  real hosts.

  --check-inventory make check_mk behave as Nagios plugins that
  checks if an inventory would find new services for the host.

  --list-hosts called without argument lists all hosts. You may
  specify one or more host groups to restrict the output to hosts
  that are in at least one of those groups.

  --list-tag prints all hosts that have all of the specified tags
  at once.

  -M, --manpage shows documentation about a check type. If
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

  --snmpwalk does a complete snmpwalk for the specifies hosts both
  on the standard MIB and the enterprises MIB and stores the
  result in the directory %s.
  
  Nagios can call check_mk without options and the hostname and its IP
  address as arguments. Much faster is using precompiled host checks,
  though.

    
""" % (check_mk_configfile,
       precompiled_hostchecks_dir,
       snmpwalks_dir,
       )


def do_create_config():
    out = file(nagios_objects_file, "w")

    if define_timeperiods != {}:
        sys.stdout.write("Generating Nagios configuration for timeperiods...")
        sys.stdout.flush()
        output_timeperiods(out)
        sys.stdout.write("OK\n")

    if generate_hostconf:
        sys.stdout.write("Generating Nagios configuration for hosts...")
        sys.stdout.flush()
        output_hostconf(out)
        sys.stdout.write("OK\n")

    sys.stdout.write("Generating Nagios configuration for services...")
    sys.stdout.flush()
    output_serviceconf(out)
    sys.stdout.write("OK\n")

    if define_contactgroups:
	sys.stdout.write("Generating Nagios configuration for contactsgroups...")
        sys.stdout.flush()
        contactgroups_to_output.update(host_contactgroups_of(all_active_hosts()))
	contactgroups_to_output.update(host_contactgroups_of(all_active_clusters()))
	output_contactgroups(contactgroups_to_output, out)
	sys.stdout.write("OK\n")

    if extra_nagios_conf:
	out.write("\n# extra_nagios_conf\n\n")
	out.write(extra_nagios_conf)

    sys.stdout.flush()
    out.close()

def do_precompile_hostchecks():
    sys.stdout.write("Precompiling host checks...")
    sys.stdout.flush()
    precompile_hostchecks()
    sys.stdout.write("OK\n")
    

def do_update():
    try:
        do_create_config()
        do_precompile_hostchecks()
        sys.stdout.write(("Successfully created Nagios configuration file %s%s%s.\n\n" +
                         "Please make sure that file will be read by Nagios.\n" +
                         "You need to restart Nagios in order to activate " +
                         "the changes.\n") % (tty_green + tty_bold, nagios_objects_file, tty_normal))

    except Exception, e:
        sys.stderr.write("Configuration Error: %s\n" % e)
        sys.exit(1)


def do_check_nagiosconfig():
    command = nagios_binary + " -v "  + nagios_config_file + " 2>&1"
    sys.stderr.write("Validating Nagios configuration...")
    if opt_verbose:
        sys.stderr.write("Running '%s'" % command)
    sys.stderr.flush()
        
    process = os.popen(command, "r")
    output = process.read()
    exit_status = process.close()
    if not exit_status:
        sys.stderr.write("OK\n")
        return True
    else:
        sys.stderr.write("ERROR:\n")
        sys.stderr.write(output)
        return False


def do_restart_nagios():
    sys.stderr.write("Restarting Nagios...")
    sys.stderr.flush()
    command = nagios_startscript + " restart 2>&1"
    process = os.popen(command, "r")
    output = process.read()
    if process.close():
        sys.stderr.write("ERROR:\n")
        raise MKGeneralException("Cannot restart Nagios")
    else:
        sys.stderr.write("OK\n")

def do_restart():
    try:
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
            os.rename(backup_path, nagios_objects_file)
            sys.exit(1)
            
        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            do_precompile_hostchecks()
            do_restart_nagios()
        else:
            sys.stderr.write("Nagios configuration is invalid. Rolling back.\n")
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            else:
                os.remove(nagios_objects_file)
            sys.exit(1)

    except Exception, e:
        try:
            if backup_path:
                os.remove(backup_path)
        except:
            pass
        sys.stderr.write("An error occurred: %s\n" % e)
        sys.exit(1)

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
                    

#   +----------------------------------------------------------------------+
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Strip off host tags from the list of all_hosts.  Host tags can be
# appended to the hostnames in all_hosts, separated by pipe symbols,
# e.g. "zbghlnx04|bgh|linux|test" and are stored in a separate
# dictionary called 'hosttags'
hosttags = {}
for taggedhost in all_hosts + clusters.keys():
    parts = taggedhost.split("|")
    hosttags[parts[0]] = parts[1:]
all_hosts_untagged = all_active_hosts()

# global helper variable needed by config output
contactgroups_to_output = set([])

# Sanity check for duplicate hostnames
seen_hostnames = set([])
for hostname in strip_tags(all_hosts + clusters.keys()):
    if hostname in seen_hostnames:
        sys.stderr.write("Error in configuration: duplicate host '%s'\n" % hostname)
        sys.exit(4)
    seen_hostnames.add(hostname)


# Do option parsing and execute main function -
# if check_mk is not called as module
if __name__ == "__main__":
    short_options = 'SHVLCURDMd:I:c:nhvpXP'
    long_options = ["help", "version", "verbose", "compile", "debug",
                    "list-checks", "list-hosts", "list-tag", "no-tcp", "cache",
		    "flush", "package", "donate", "snmpwalk", "usewalk",
                    "no-cache", "update", "restart", "dump", "fake-dns=",
                    "man", "nowiki", "config-check", "backup=", "restore=",
                    "check-inventory=", "timeperiods", "paths" ]

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(1)
      
    done = False
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
        elif o == '--fake-dns':
            fake_dns = a
        elif o == '--usewalk':
            opt_use_snmp_walk = True
        elif o == '--nowiki':
            opt_nowiki = True
        elif o == '--debug':
            opt_debug = True

    # Perform actions (major modes)
    try:
      for o,a in opts:
        if o in [ '-h', '--help' ]:
            usage()
            sys.exit(0)
        elif o in [ '-V', '--version' ]:
            print_version()
            sys.exit(0)
        elif o in [ '-X', '--config-check' ]:
            sys.exit(0) # already done
        elif o == '-S':
            # import profile
            # profile.run('output_serviceconf()')
            output_serviceconf()
            done = True
        elif o == '-H':
            # import profile
            # profile.run('output_hostconf()')
            output_hostconf()
            done = True
        elif o == '--timeperiods':
            output_timeperiods()
            done = True
        elif o in [ '-C', '--compile' ]:
            precompile_hostchecks()
            done = True
        elif o in [ '-U', '--update' ] :
            do_update()
            done = True
        elif o in [ '-R', '--restart' ] :
            do_restart()
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
        elif o == '--donate':
            do_donation()
            done = True
        elif o == '--snmpwalk':
            do_snmpwalk(args)
            done = True
        elif o in [ '-M', '--man' ]:
            if len(args) > 0:
                show_check_manual(args[0])
            else:
                list_all_manuals()
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
        elif o == '-I':
            if a == 'list':
                print "Checktypes available for inventory are: %s" % (",".join(inventorable_checktypes()))
            else:	
		if a == "allsnmp" or a == "snmp":
		    do_snmp_scan(args) 
		else:
		    if a == 'alltcp' or a == "tcp":
			checknames = inventorable_checktypes(False)
			opt_no_snmp_hosts = True
		    else:
			checknames = a.split(',')
		    if len(checknames) == 0:
			print "Please specify check types."
			usage()
			sys.exit(1)
		    for checkname in checknames:
			make_inventory(checkname, args)
            done = True
        elif o == '--check-inventory':
            check_inventory(a)
            done = True

        
    except MKGeneralException, e:
        sys.stderr.write("%s\n" % e)
        if opt_debug:
            raise
        sys.exit(3)

    if done:
        sys.exit(0)
    elif len(args) == 0 or len(args) > 2:
        usage()
        sys.exit(1)
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

        do_check(hostname, ipaddress)
