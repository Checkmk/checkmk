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

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

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
debug_log                          = False # deprecated
monitoring_host                    = None # deprecated
max_num_processes                  = 50

# SNMP communities and encoding
has_inline_snmp                    = False # is set to True by inline_snmp module, when available
use_inline_snmp                    = True
snmp_limit_oid_range               = [] # Ruleset to recduce fetched OIDs of a check, only inline SNMP
record_inline_snmp_stats           = False
snmp_default_community             = 'public'
snmp_communities                   = []
snmp_timing                        = []
snmp_character_encodings           = []
explicit_snmp_communities          = {} # override the rule based configuration

# RRD creation (only with CMC)
cmc_log_rrdcreation                = None # also: "terse", "full"
cmc_host_rrd_config                = [] # Rule for per-host configuration of RRDs
cmc_service_rrd_config             = [] # Rule for per-service configuration of RRDs

# Inventory and inventory checks
inventory_check_interval           = None # Nagios intervals (4h = 240)
inventory_check_severity           = 1    # warning
inventory_check_do_scan            = True # include SNMP scan for SNMP devices
inventory_max_cachefile_age        = 120  # seconds
inventory_check_autotrigger        = True # Automatically trigger inv-check after automation-inventory
always_cleanup_autochecks          = None # For compatiblity with old configuration

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
clustered_services_mapping           = [] # new for 1.2.5i1 Wato Rule
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
check_mk_agent_target_versions       = [] # Rule for defining expected version for agents
check_periods                        = []
snmp_check_interval                  = []
inv_exports                          = {} # Rulesets for inventory export hooks
notification_parameters              = {} # Rulesets for parameters of notification scripts
use_new_descriptions_for             = []

# Rulesets for agent bakery
agent_config                         = {}
bake_agents_on_restart               = False
