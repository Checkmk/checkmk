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

from typing import (  # pylint: disable=unused-import
    Dict as _Dict, List as _List, Optional as _Optional, Text as _Text,
)

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

# TODO: Remove the duplication with cmk.base.config
_ALL_HOSTS = ['@all']  # physical and cluster hosts
_NEGATE = '@negate'  # negation in boolean lists

monitoring_core = "nagios"  # other option: "cmc"
mkeventd_enabled = False  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports = []  # type: _List
agent_encryption = []  # type: _List
# UDP ports used for SNMP
snmp_ports = []  # type: _List
tcp_connect_timeout = 5.0
tcp_connect_timeouts = []  # type: _List
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking = "abort"  # also possible: "wait", None
check_submission = "file"  # alternative: "pipe"
agent_min_version = 0  # warn, if plugin has not at least version
default_host_group = 'check_mk'

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
# Ruleset for translating piggyback host names
piggyback_translation = []  # type: _List
# Ruleset for translating service descriptions
service_description_translation = []  # type: _List
simulation_mode = False
fake_dns = None  # type: _Optional[str]
agent_simulator = False
perfdata_format = "pnp"  # also possible: "standard"
check_mk_perfdata_with_times = True
# TODO: Remove these options?
debug_log = False  # deprecated
monitoring_host = None  # deprecated
max_num_processes = 50
fallback_agent_output_encoding = 'latin-1'
stored_passwords = {}  # type: _Dict
# Collection of predefined rule conditions. For the moment this setting is only stored
# in this config domain but not used by the base code. The WATO logic for writing out
# rule.mk files is resolving the predefined conditions.
predefined_conditions = {}  # type: _Dict
# Global setting for managing HTTP proxy configs
http_proxies = {}  # type: _Dict

# SNMP communities and encoding
use_inline_snmp = True
# Ruleset to disable Inline-SNMP per host when use_inline_snmp is enabled.
non_inline_snmp_hosts = []  # type: _List

# Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_limit_oid_range = []  # type: _List
# Ruleset to customize bulk size
snmp_bulk_size = []  # type: _List
record_inline_snmp_stats = False
snmp_default_community = 'public'
snmp_communities = []  # type: _List
# override the rule based configuration
explicit_snmp_communities = {}  # type: _Dict
snmp_timing = []  # type: _List
snmp_character_encodings = []  # type: _List

# Custom variables
explicit_service_custom_variables = {}  # type: _Dict

# Management board settings
# Ruleset to specify management board settings
management_board_config = []  # type: _List
# Mapping from hostname to management board protocol
management_protocol = {}  # type: _Dict
# Mapping from hostname to SNMP credentials
management_snmp_credentials = {}  # type: _Dict
# Mapping from hostname to IPMI credentials
management_ipmi_credentials = {}  # type: _Dict

# RRD creation (only with CMC)
cmc_log_rrdcreation = None  # also: "terse", "full"
# Rule for per-host configuration of RRDs
cmc_host_rrd_config = []  # type: _List
# Rule for per-service configuration of RRDs
cmc_service_rrd_config = []  # type: _List

# Inventory and inventory checks
inventory_check_interval = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_check_do_scan = True  # include SNMP scan for SNMP devices
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration

periodic_discovery = []  # type: _List

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
}  # type: _Dict[str, _List]
checks = []  # type: _List
static_checks = {}  # type: _Dict
check_parameters = []  # type: _List
checkgroup_parameters = {}  # type: _Dict
# for HW/SW-Inventory
inv_parameters = {}  # type: _Dict
# WATO variant for fully formalized checks
active_checks = {}  # type: _Dict
# WATO variant for datasource_programs
special_agents = {}  # type: _Dict
# WATO variant for free-form custom checks without formalization
custom_checks = []  # type: _List
all_hosts = []  # type: _List
# store host tag config per host
host_tags = {}  # type: _Dict
# store explicit host labels per host
host_labels = {}  # type: _Dict
# Assign labels via ruleset to hosts
host_label_rules = []  # type: _List
# Asssing labels via ruleset to services
service_label_rules = []  # type: _List
# TODO: This is a derived variable. Should be handled like others
# (hosttags, service_service_levels, ...)
# Map of hostnames to .mk files declaring the hosts (e.g. /wato/hosts.mk)
host_paths = {}  # type: _Dict
snmp_hosts = [
    (['snmp'], _ALL_HOSTS),
]  # type: _List
tcp_hosts = [
    (['tcp'], _ALL_HOSTS),
    (_NEGATE, ['snmp'], _ALL_HOSTS),
    # Match all those that don't have ping and don't have no-agent set
    (['!ping', '!no-agent'], _ALL_HOSTS),
]  # type: _List
bulkwalk_hosts = []  # type: _List
snmpv2c_hosts = []  # type: _List
snmp_without_sys_descr = []  # type: _List
snmpv3_contexts = []  # type: _List
usewalk_hosts = []  # type: _List
# use host name as ip address for these hosts
dyndns_hosts = []  # type: _List
primary_address_family = []  # type: _List
# exclude from inventory
ignored_checktypes = []  # type: _List
# exclude from inventory
ignored_services = []  # type: _List
# exclude from inventory
ignored_checks = []  # type: _List
host_groups = []  # type: _List
service_groups = []  # type: _List
service_contactgroups = []  # type: _List
# deprecated, will be removed soon.
service_notification_periods = []  # type: _List
# deprecated, will be removed soon.
host_notification_periods = []  # type: _List
host_contactgroups = []  # type: _List
parents = []  # type: _List
define_hostgroups = None
define_servicegroups = None
define_contactgroups = None  # type: _Optional[_Dict[str, _Text]]
contactgroup_members = {}  # type: _Dict
contacts = {}  # type: _Dict
# needed for WATO
timeperiods = {}  # type: _Dict
clusters = {}  # type: _Dict
clustered_services = []  # type: _List
# new in 1.1.4
clustered_services_of = {}  # type: _Dict
# new for 1.2.5i1 Wato Rule
clustered_services_mapping = []  # type: _List
datasource_programs = []  # type: _List
service_dependencies = []  # type: _List
# mapping from hostname to IPv4 address
ipaddresses = {}  # type: _Dict
# mapping from hostname to IPv6 address
ipv6addresses = {}  # type: _Dict
# mapping from hostname to addtional IPv4 addresses
additional_ipv4addresses = {}  # type: _Dict
# mapping from hostname to addtional IPv6 addresses
additional_ipv6addresses = {}  # type: _Dict
only_hosts = None
distributed_wato_site = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf = {}  # type: _Dict
explicit_host_conf = {}  # type: _Dict
extra_service_conf = {}  # type: _Dict
extra_nagios_conf = ""
service_descriptions = {}  # type: _Dict
# needed by WATO, ignored by Check_MK
host_attributes = {}  # type: _Dict
# special parameters for host/PING check_command
ping_levels = []  # type: _List
# alternative host check instead of check_icmp
host_check_commands = []  # type: _List
# time settings for piggybacked hosts
piggybacked_host_files = []  # type: _List
# Rule for specifying CMK's exit status in case of various errors
check_mk_exit_status = []  # type: _List
# Rule for defining expected version for agents
check_mk_agent_target_versions = []  # type: _List
check_periods = []  # type: _List
snmp_check_interval = []  # type: _List
# Rulesets for inventory export hooks
inv_exports = {}  # type: _Dict
# Rulesets for parameters of notification scripts
notification_parameters = {}  # type: _Dict
use_new_descriptions_for = []  # type: _List
# Custom user icons / actions to be configured
host_icons_and_actions = []  # type: _List
# Custom user icons / actions to be configured
service_icons_and_actions = []  # type: _List
# Match all ruleset to assign custom service attributes
custom_service_attributes = []  # type: _List
# Assign tags to services
service_tag_rules = []  # type: _List

# Rulesets for agent bakery
agent_config = {}  # type: _Dict
bake_agents_on_restart = False

# Kept for compatibility, but are deprecated and not used anymore
extra_summary_host_conf = {}  # type: _Dict
extra_summary_service_conf = {}  # type: _Dict
summary_host_groups = []  # type: _List
# service groups for aggregated services
summary_service_groups = []  # type: _List
# service contact groups for aggregated services
summary_service_contactgroups = []  # type: _List
summary_host_notification_periods = []  # type: _List
summary_service_notification_periods = []  # type: _List
service_aggregations = []  # type: _List
non_aggregated_hosts = []  # type: _List
aggregate_check_mk = False
aggregation_output_format = "multiline"  # new in 1.1.6. Possible also: "multiline"
aggr_summary_hostname = "%s-s"
status_data_inventory = []  # type: _List
legacy_checks = []  # type: _List
