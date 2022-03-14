#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict as _Dict
from typing import List as _List
from typing import Literal as _Literal
from typing import Optional as _Optional

from cmk.utils.password_store import Password
from cmk.utils.type_defs import Ruleset, TagConfigSpec, TagsOfHosts, TimeperiodSpecs

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

# TODO: Remove the duplication with cmk.base.config
_ALL_HOSTS = ["@all"]  # physical and cluster hosts
_NEGATE = "@negate"  # negation in boolean lists

monitoring_core = "nagios"  # other option: "cmc"
mkeventd_enabled = False  # Set by OMD hook
pnp4nagios_enabled = True  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports: _List = []
agent_encryption: _List = []
agent_exclude_sections: _List = []
# UDP ports used for SNMP
snmp_ports: _List = []
tcp_connect_timeout = 5.0
tcp_connect_timeouts: _List = []
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking = "abort"  # also possible: "wait", None
check_submission = "file"  # alternative: "pipe"
default_host_group = "check_mk"

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
# Ruleset for translating piggyback host names
piggyback_translation: _List = []
# Ruleset for translating service descriptions
service_description_translation: _List = []
simulation_mode = False
fake_dns: _Optional[str] = None
agent_simulator = False
perfdata_format = "pnp"  # also possible: "standard"
check_mk_perfdata_with_times = True
# TODO: Remove these options?
debug_log = False  # deprecated
monitoring_host = None  # deprecated
max_num_processes = 50
fallback_agent_output_encoding = "latin-1"
stored_passwords: _Dict[str, Password] = {}
# Collection of predefined rule conditions. For the moment this setting is only stored
# in this config domain but not used by the base code. The WATO logic for writing out
# rule.mk files is resolving the predefined conditions.
predefined_conditions: _Dict = {}
# Global setting for managing HTTP proxy configs
http_proxies: _Dict = {}

# SNMP communities and encoding

# Global config for SNMP Backend
snmp_backend_default: str = "inline"
# Deprecated: Replaced by snmp_backend_hosts
use_inline_snmp: bool = True

# Ruleset to enable specific SNMP Backend for each host.
snmp_backend_hosts: _List = []
# Deprecated: Replaced by snmp_backend_hosts
non_inline_snmp_hosts: _List = []

# Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_limit_oid_range: _List = []
# Ruleset to customize bulk size
snmp_bulk_size: _List = []
snmp_default_community = "public"
snmp_communities: _List = []
# override the rule based configuration
explicit_snmp_communities: _Dict = {}
snmp_timing: _List = []
snmp_character_encodings: _List = []

# Custom variables
explicit_service_custom_variables: _Dict = {}

# Management board settings
# Ruleset to specify management board settings
management_board_config: _List = []
# Mapping from hostname to management board protocol
management_protocol: _Dict = {}
# Mapping from hostname to SNMP credentials
management_snmp_credentials: _Dict = {}
# Mapping from hostname to IPMI credentials
management_ipmi_credentials: _Dict = {}
# Ruleset to specify whether or not to use bulkwalk
management_bulkwalk_hosts: _List = []

# RRD creation (only with CMC)
cmc_log_rrdcreation = None  # also: "terse", "full"
# Rule for per-host configuration of RRDs
cmc_host_rrd_config: _List = []
# Rule for per-service configuration of RRDs
cmc_service_rrd_config: _List = []

# Inventory and inventory checks
inventory_check_interval = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
inv_retention_intervals: Ruleset = []
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration

periodic_discovery: _List = []

# Nagios templates and other settings concerning generation
# of Nagios configuration files. No need to change these values.
# Better adopt the content of the templates
host_template = "check_mk_host"
cluster_template = "check_mk_cluster"
pingonly_template = "check_mk_pingonly"
active_service_template = "check_mk_active"
inventory_check_template = "check_mk_inventory"
passive_service_template = "check_mk_passive"
passive_service_template_perf = "check_mk_passive_perf"
summary_service_template = "check_mk_summarized"
service_dependency_template = "check_mk"
generate_hostconf = True
generate_dummy_commands = True
dummy_check_commandline = 'echo "ERROR - you did an active check on this service - please disable active checks" && exit 1'
nagios_illegal_chars = "`;~!$%^&*|'\"<>?,="
cmc_illegal_chars = ";\t"  # Tab is an illegal character for CMC and semicolon breaks metric system

# Data to be defined in main.mk
tag_config: TagConfigSpec = {
    "aux_tags": [],
    "tag_groups": [],
}
checks: _List = []
static_checks: _Dict = {}
check_parameters: _List = []
checkgroup_parameters: _Dict = {}
# for HW/SW-Inventory
inv_parameters: _Dict = {}
# WATO variant for fully formalized checks
active_checks: _Dict = {}
# WATO variant for datasource_programs
special_agents: _Dict = {}
# WATO variant for free-form custom checks without formalization
custom_checks: _List = []
all_hosts: _List = []
# store host tag config per host
host_tags: TagsOfHosts = {}
# store explicit host labels per host
host_labels: _Dict = {}
# Assign labels via ruleset to hosts
host_label_rules: _List = []
# Asssing labels via ruleset to services
service_label_rules: _List = []
# TODO: This is a derived variable. Should be handled like others
# (hosttags, service_service_levels, ...)
# Map of hostnames to .mk files declaring the hosts (e.g. /wato/hosts.mk)
host_paths: _Dict = {}
snmp_hosts: _List = [
    (["snmp"], _ALL_HOSTS),
]
tcp_hosts: _List = [
    (["tcp"], _ALL_HOSTS),
    (_NEGATE, ["snmp"], _ALL_HOSTS),
    # Match all those that don't have ping and don't have no-agent set
    (["!ping", "!no-agent"], _ALL_HOSTS),
]
cmk_agent_connection: _Dict = {}
bulkwalk_hosts: _List = []
snmpv2c_hosts: _List = []
snmp_without_sys_descr: _List = []
snmpv3_contexts: _List = []
usewalk_hosts: _List = []
# use host name as ip address for these hosts
dyndns_hosts: _List = []
primary_address_family: _List = []
# exclude from inventory
ignored_checktypes: _List = []
# exclude from inventory
ignored_services: _List = []
# exclude from inventory
ignored_checks: _List = []
host_groups: _List = []
service_groups: _List = []
service_contactgroups: _List = []
# deprecated, will be removed soon.
service_notification_periods: _List = []
# deprecated, will be removed soon.
host_notification_periods: _List = []
host_contactgroups: _List = []
parents: _List = []
define_hostgroups: _Dict[str, str] = {}
define_servicegroups: _Dict[str, str] = {}
define_contactgroups: _Dict[str, str] = {}
contactgroup_members: _Dict = {}
contacts: _Dict = {}
# needed for WATO
timeperiods: TimeperiodSpecs = {}
clusters: _Dict = {}
clustered_services: _List = []
# new in 1.1.4
clustered_services_of: _Dict = {}
# new for 1.2.5i1 Wato Rule
clustered_services_mapping: _List = []
clustered_services_configuration: _List = []
datasource_programs: _List = []
service_dependencies: _List = []
# mapping from hostname to IPv4 address
ipaddresses: _Dict = {}
# mapping from hostname to IPv6 address
ipv6addresses: _Dict = {}
# mapping from hostname to addtional IPv4 addresses
additional_ipv4addresses: _Dict = {}
# mapping from hostname to addtional IPv6 addresses
additional_ipv6addresses: _Dict = {}
only_hosts = None
distributed_wato_site = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf: _Dict = {}
explicit_host_conf: _Dict = {}
extra_service_conf: _Dict = {}
extra_nagios_conf = ""
service_descriptions: _Dict = {}
# needed by WATO, ignored by Checkmk
host_attributes: _Dict = {}
# special parameters for host/PING check_command
ping_levels: _List = []
# alternative host check instead of check_icmp
host_check_commands: _List = []
# time settings for piggybacked hosts
piggybacked_host_files: _List = []
# Rule for specifying CMK's exit status in case of various errors
check_mk_exit_status: _List = []
# Rule for defining expected version for agents
check_mk_agent_target_versions: _List = []
check_periods: _List = []
snmp_check_interval: _List = []
snmp_exclude_sections: _List = []
# Rulesets for inventory export hooks
inv_exports: _Dict = {}
# Rulesets for parameters of notification scripts
notification_parameters: _Dict = {}
use_new_descriptions_for: _List = []
# Custom user icons / actions to be configured
host_icons_and_actions: _List = []
# Custom user icons / actions to be configured
service_icons_and_actions: _List = []
# Match all ruleset to assign custom service attributes
custom_service_attributes: _List = []
# Assign tags to services
service_tag_rules: _List = []

# Rulesets for agent bakery
agent_config: _Dict = {}
bake_agents_on_restart = False

# Kept for compatibility, but are deprecated and not used anymore
extra_summary_host_conf: _Dict = {}
extra_summary_service_conf: _Dict = {}
summary_host_groups: _List = []
# service groups for aggregated services
summary_service_groups: _List = []
# service contact groups for aggregated services
summary_service_contactgroups: _List = []
summary_host_notification_periods: _List = []
summary_service_notification_periods: _List = []
service_aggregations: _List = []
non_aggregated_hosts: _List = []
aggregate_check_mk = False
aggregation_output_format = "multiline"  # new in 1.1.6. Possible also: "multiline"
aggr_summary_hostname = "%s-s"
status_data_inventory: _List = []
legacy_checks: _List = []

logwatch_rules: _List = []

config_storage_format: _Literal["standard", "raw", "pickle"] = "pickle"
