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

import typing as _typing  # pylint: disable=unused-import

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

# TODO: Remove the duplication with cmk_base.config
_ALL_HOSTS = ['@all']  # physical and cluster hosts
_NEGATE = '@negate'  # negation in boolean lists

monitoring_core = "nagios"  # other option: "cmc"
mkeventd_enabled = False  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports = []
agent_encryption = []
snmp_ports = []  # UDP ports used for SNMP
tcp_connect_timeout = 5.0
tcp_connect_timeouts = []
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking = "abort"  # also possible: "wait", None
check_submission = "file"  # alternative: "pipe"
agent_min_version = 0  # warn, if plugin has not at least version
default_host_group = 'check_mk'

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
piggyback_translation = []  # Ruleset for translating piggyback host names
service_description_translation = []  # Ruleset for translating service descriptions
simulation_mode = False
fake_dns = None  # type: _typing.Optional[str]
agent_simulator = False
perfdata_format = "pnp"  # also possible: "standard"
check_mk_perfdata_with_times = True
# TODO: Remove these options?
debug_log = False  # deprecated
monitoring_host = None  # deprecated
max_num_processes = 50
fallback_agent_output_encoding = 'latin1'
stored_passwords = {}
# Collection of predefined rule conditions. For the moment this setting is only stored
# in this config domain but not used by the base code. The WATO logic for writing out
# rule.mk files is resolving the predefined conditions.
predefined_conditions = {}
http_proxies = {}  # Global setting for managing HTTP proxy configs

# SNMP communities and encoding
use_inline_snmp = True
non_inline_snmp_hosts = []  # Ruleset to disable Inline-SNMP per host when
# use_inline_snmp is enabled.

snmp_limit_oid_range = []  # Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_bulk_size = []  # Ruleset to customize bulk size
record_inline_snmp_stats = False
snmp_default_community = 'public'
snmp_communities = []
explicit_snmp_communities = {}  # override the rule based configuration
snmp_timing = []
snmp_character_encodings = []

# Custom variables
explicit_service_custom_variables = {}

# Management board settings
management_board_config = []  # Ruleset to specify management board settings
management_protocol = {}  # Mapping from hostname to management board protocol
management_snmp_credentials = {}  # Mapping from hostname to SNMP credentials
management_ipmi_credentials = {}  # Mapping from hostname to IPMI credentials

# RRD creation (only with CMC)
cmc_log_rrdcreation = None  # also: "terse", "full"
cmc_host_rrd_config = []  # Rule for per-host configuration of RRDs
cmc_service_rrd_config = []  # Rule for per-service configuration of RRDs

# Inventory and inventory checks
inventory_check_interval = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_check_do_scan = True  # include SNMP scan for SNMP devices
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration

periodic_discovery = []

# Nagios templates and other settings concerning generation
# of Nagios configuration files. No need to change these values.
# Better adopt the content of the templates
host_template = 'check_mk_host'
cluster_template = 'check_mk_cluster'
pingonly_template = 'check_mk_pingonly'
active_service_template = 'check_mk_active'
inventory_check_template = 'check_mk_inventory'
passive_service_template = 'check_mk_passive'
passive_service_template_perf = 'check_mk_passive_perf'
summary_service_template = 'check_mk_summarized'
service_dependency_template = 'check_mk'
generate_hostconf = True
generate_dummy_commands = True
dummy_check_commandline = 'echo "ERROR - you did an active check on this service - please disable active checks" && exit 1'
nagios_illegal_chars = '`;~!$%^&*|\'"<>?,()='

# Data to be defined in main.mk
tag_config = {
    "aux_tags": [],
    "tag_groups": [],
}
checks = []
static_checks = {}
check_parameters = []
checkgroup_parameters = {}
inv_parameters = {}  # for HW/SW-Inventory
active_checks = {}  # WATO variant for fully formalized checks
special_agents = {}  # WATO variant for datasource_programs
custom_checks = []  # WATO variant for free-form custom checks without formalization
all_hosts = []
host_tags = {}  # store host tag config per host
host_labels = {}  # store explicit host labels per host
host_label_rules = []  # Assign labels via ruleset to hosts
service_label_rules = []  # Asssing labels via ruleset to services
# TODO: This is a derived variable. Should be handled like others
# (hosttags, service_service_levels, ...)
host_paths = {}  # Map of hostnames to .mk files declaring the hosts (e.g. /wato/hosts.mk)
snmp_hosts = [
    (['snmp'], _ALL_HOSTS),
]
tcp_hosts = [
    (['tcp'], _ALL_HOSTS),
    (_NEGATE, ['snmp'], _ALL_HOSTS),
    # Match all those that don't have ping and don't have no-agent set
    (['!ping', '!no-agent'], _ALL_HOSTS),
]
bulkwalk_hosts = []
snmpv2c_hosts = []
snmp_without_sys_descr = []
snmpv3_contexts = []
usewalk_hosts = []
dyndns_hosts = []  # use host name as ip address for these hosts
primary_address_family = []
ignored_checktypes = []  # exclude from inventory
ignored_services = []  # exclude from inventory
ignored_checks = []  # exclude from inventory
host_groups = []
service_groups = []
service_contactgroups = []
service_notification_periods = []  # deprecated, will be removed soon.
host_notification_periods = []  # deprecated, will be removed soon.
host_contactgroups = []
parents = []
define_hostgroups = None
define_servicegroups = None
define_contactgroups = None
contactgroup_members = {}
contacts = {}
timeperiods = {}  # needed for WATO
clusters = {}
clustered_services = []
clustered_services_of = {}  # new in 1.1.4
clustered_services_mapping = []  # new for 1.2.5i1 Wato Rule
datasource_programs = []
service_dependencies = []
ipaddresses = {}  # mapping from hostname to IPv4 address
ipv6addresses = {}  # mapping from hostname to IPv6 address
additional_ipv4addresses = {}  # mapping from hostname to addtional IPv4 addresses
additional_ipv6addresses = {}  # mapping from hostname to addtional IPv6 addresses
only_hosts = None
distributed_wato_site = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf = {}
extra_service_conf = {}
extra_nagios_conf = ""
service_descriptions = {}
host_attributes = {}  # needed by WATO, ignored by Check_MK
ping_levels = []  # special parameters for host/PING check_command
host_check_commands = []  # alternative host check instead of check_icmp
check_mk_exit_status = []  # Rule for specifying CMK's exit status in case of various errors
check_mk_agent_target_versions = []  # Rule for defining expected version for agents
check_periods = []
snmp_check_interval = []
inv_exports = {}  # Rulesets for inventory export hooks
notification_parameters = {}  # Rulesets for parameters of notification scripts
use_new_descriptions_for = []
host_icons_and_actions = []  # Custom user icons / actions to be configured
service_icons_and_actions = []  # Custom user icons / actions to be configured
custom_service_attributes = []  # Match all ruleset to assign custom service attributes
service_tag_rules = []  # Assign tags to services

# Rulesets for agent bakery
agent_config = {}
bake_agents_on_restart = False

# Kept for compatibility, but are deprecated and not used anymore
extra_summary_host_conf = {}
extra_summary_service_conf = {}
summary_host_groups = []
summary_service_groups = []  # service groups for aggregated services
summary_service_contactgroups = []  # service contact groups for aggregated services
summary_host_notification_periods = []
summary_service_notification_periods = []
service_aggregations = []
non_aggregated_hosts = []
aggregate_check_mk = False
aggregation_output_format = "multiline"  # new in 1.1.6. Possible also: "multiline"
aggr_summary_hostname = "%s-s"
status_data_inventory = []
legacy_checks = []
