#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Final, Literal

from cmk.utils.password_store import Password
from cmk.utils.store.host_storage import FolderAttributes
from cmk.utils.type_defs import (
    CheckPluginNameStr,
    Contact,
    ContactgroupName,
    ContactName,
    HostAddress,
    HostgroupName,
    HostName,
    Labels,
    Ruleset,
    ServicegroupName,
    ServiceName,
    TagConfigSpec,
    TagsOfHosts,
    TimeperiodSpecs,
)

from cmk.snmplib.type_defs import SNMPCredentials

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

# TODO: Remove the duplication with cmk.base.config
_ALL_HOSTS: Final = ["@all"]  # physical and cluster hosts
_NEGATE: Final = "@negate"  # negation in boolean lists

monitoring_core: Literal["nagios", "cmc"] = "nagios"
mkeventd_enabled = False  # Set by OMD hook
pnp4nagios_enabled = True  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports: Ruleset[int] = []
agent_encryption: Ruleset[str | None] = []
encryption_handling: Ruleset[object] = []
agent_exclude_sections: Ruleset[object] = []
# UDP ports used for SNMP
snmp_ports: Ruleset[object] = []
tcp_connect_timeout = 5.0
tcp_connect_timeouts: Ruleset[object] = []
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking: Literal["abort", "wait"] | None = "abort"
check_submission: Literal["file", "pipe"] = "file"
default_host_group = "check_mk"

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
# Ruleset for translating piggyback host names
piggyback_translation: Ruleset[object] = []
# Ruleset for translating service descriptions
service_description_translation: Ruleset[object] = []
simulation_mode = False
fake_dns: str | None = None
agent_simulator = False
perfdata_format: Literal["pnp", "standard"] = "pnp"
check_mk_perfdata_with_times = True
# TODO: Remove these options?
debug_log = False  # deprecated
monitoring_host: str | None = None  # deprecated
max_num_processes = 50
fallback_agent_output_encoding = "latin-1"
stored_passwords: dict[str, Password] = {}
# Collection of predefined rule conditions. For the moment this setting is only stored
# in this config domain but not used by the base code. The WATO logic for writing out
# rule.mk files is resolving the predefined conditions.
predefined_conditions: dict = {}
# Global setting for managing HTTP proxy configs
http_proxies: dict[str, dict[str, str]] = {}

# SNMP communities and encoding

# Global config for SNMP Backend
snmp_backend_default: Literal["inline", "classic"] = "inline"
# Deprecated: Replaced by snmp_backend_hosts
use_inline_snmp: bool = True

# Ruleset to enable specific SNMP Backend for each host.
snmp_backend_hosts: Ruleset[object] = []
# Deprecated: Replaced by snmp_backend_hosts
non_inline_snmp_hosts: Ruleset[object] = []

# Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_limit_oid_range: Ruleset[object] = []
# Ruleset to customize bulk size
snmp_bulk_size: Ruleset[object] = []
snmp_default_community = "public"
snmp_communities: Ruleset[object] = []
# override the rule based configuration
explicit_snmp_communities: dict[HostName, SNMPCredentials] = {}
snmp_timing: Ruleset[object] = []
snmp_character_encodings: Ruleset[object] = []

# Custom variables
explicit_service_custom_variables: dict[tuple[HostName, ServiceName], dict[str, str]] = {}

# Management board settings
# Ruleset to specify management board settings
management_board_config: Ruleset[object] = []
# Mapping from hostname to management board protocol
management_protocol: dict[HostName, Literal["snmp", "ipmi"]] = {}
# Mapping from hostname to SNMP credentials
management_snmp_credentials: dict[HostName, SNMPCredentials] = {}
# Mapping from hostname to IPMI credentials
management_ipmi_credentials: dict[HostName, dict[str, str]] = {}
# Ruleset to specify whether or not to use bulkwalk
management_bulkwalk_hosts: Ruleset[object] = []

# RRD creation (only with CMC)
cmc_log_rrdcreation: Literal["terse", "full"] | None = None
# Rule for per-host configuration of RRDs
cmc_host_rrd_config: Ruleset[object] = []
# Rule for per-service configuration of RRDs
cmc_service_rrd_config: Ruleset[object] = []

# Inventory and inventory checks
inventory_check_interval: int | None = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
inv_retention_intervals: Ruleset[object] = []
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration

periodic_discovery: Ruleset[object] = []

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
checks: Ruleset[object] = []
static_checks: dict[str, Ruleset[object]] = {}
check_parameters: Ruleset[object] = []
checkgroup_parameters: dict[str, Ruleset[object]] = {}
# for HW/SW-Inventory
inv_parameters: dict[str, Ruleset[object]] = {}
# WATO variant for fully formalized checks
active_checks: dict[str, Ruleset[object]] = {}
# WATO variant for datasource_programs
special_agents: dict[str, Ruleset[object]] = {}
# WATO variant for free-form custom checks without formalization
custom_checks: Ruleset[object] = []
all_hosts: list = []
# store host tag config per host
host_tags: TagsOfHosts = {}
# store explicit host labels per host
host_labels: dict[HostName, Labels] = {}
# Assign labels via ruleset to hosts
host_label_rules: Ruleset[dict[str, str]] = []
# Asssing labels via ruleset to services
service_label_rules: Ruleset[dict[str, str]] = []
# TODO: This is a derived variable. Should be handled like others
# (hosttags, service_service_levels, ...)
# Map of hostnames to .mk files declaring the hosts (e.g. /wato/hosts.mk)
host_paths: dict[HostName, str] = {}
snmp_hosts: list = [
    (["snmp"], _ALL_HOSTS),
]
tcp_hosts: list = [
    (["tcp"], _ALL_HOSTS),
    (_NEGATE, ["snmp"], _ALL_HOSTS),
    # Match all those that don't have ping and don't have no-agent set
    (["!ping", "!no-agent"], _ALL_HOSTS),
]
cmk_agent_connection: dict[HostName, Literal["pull-agent", "push-agent"]] = {}
bulkwalk_hosts: Ruleset[object] = []
snmpv2c_hosts: Ruleset[object] = []
snmp_without_sys_descr: Ruleset[object] = []
snmpv3_contexts: Ruleset[object] = []
usewalk_hosts: Ruleset[object] = []
# use host name as ip address for these hosts
dyndns_hosts: Ruleset[object] = []
primary_address_family: Ruleset[object] = []
# exclude from inventory
ignored_checktypes: list[str] = []
# exclude from inventory
ignored_services: Ruleset[object] = []
# exclude from inventory
ignored_checks: Ruleset[object] = []
host_groups: Ruleset[object] = []
service_groups: Ruleset[object] = []
service_contactgroups: Ruleset[object] = []
# deprecated, will be removed soon.
service_notification_periods: Ruleset[object] = []
# deprecated, will be removed soon.
host_notification_periods: Ruleset[object] = []
host_contactgroups: Ruleset[object] = []
parents: Ruleset[object] = []
define_hostgroups: dict[HostgroupName, str] = {}
define_servicegroups: dict[ServicegroupName, str] = {}
define_contactgroups: dict[ContactgroupName, str] = {}
contactgroup_members: dict[ContactgroupName, list[ContactName]] = {}
contacts: dict[ContactName, Contact] = {}
# needed for WATO
timeperiods: TimeperiodSpecs = {}
clusters: dict[HostName, list[HostName]] = {}
clustered_services: Ruleset[object] = []
# new in 1.1.4
clustered_services_of: dict = {}
# new for 1.2.5i1 Wato Rule
clustered_services_mapping: Ruleset[object] = []
clustered_services_configuration: Ruleset[object] = []
datasource_programs: Ruleset[object] = []
service_dependencies: list = []
# mapping from hostname to IPv4 address
ipaddresses: dict[HostName, HostAddress] = {}
# mapping from hostname to IPv6 address
ipv6addresses: dict[HostName, HostAddress] = {}
# mapping from hostname to addtional IPv4 addresses
additional_ipv4addresses: dict[HostName, list[HostAddress]] = {}
# mapping from hostname to addtional IPv6 addresses
additional_ipv6addresses: dict[HostName, list[HostAddress]] = {}
only_hosts: Ruleset[object] | None = None
distributed_wato_site: str | None = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf: dict[str, Ruleset[str]] = {}
explicit_host_conf: dict[str, dict[HostName, Any]] = {}
extra_service_conf: dict[str, Ruleset[object]] = {}
extra_nagios_conf = ""
service_descriptions: dict[str, str] = {}
# needed by WATO, ignored by Checkmk
host_attributes: dict[HostName, dict[str, Any]] = {}
# special parameters for host/PING check_command
ping_levels: Ruleset[object] = []
# alternative host check instead of check_icmp
host_check_commands: Ruleset[object] = []
# time settings for piggybacked hosts
piggybacked_host_files: Ruleset[object] = []
# Rule for specifying CMK's exit status in case of various errors
check_mk_exit_status: Ruleset[object] = []
# Rule for defining expected version for agents
check_mk_agent_target_versions: Ruleset[object] = []
check_periods: Ruleset[object] = []
snmp_check_interval: Ruleset[object] = []
snmp_exclude_sections: Ruleset[object] = []
# Rulesets for parameters of notification scripts
notification_parameters: dict[str, Ruleset[object]] = {}
use_new_descriptions_for: list[CheckPluginNameStr] = []
# Custom user icons / actions to be configured
host_icons_and_actions: Ruleset[object] = []
# Custom user icons / actions to be configured
service_icons_and_actions: Ruleset[object] = []
# Match all ruleset to assign custom service attributes
custom_service_attributes: Ruleset[object] = []
# Assign tags to services
service_tag_rules: Ruleset[object] = []

# Rulesets for agent bakery
agent_config: dict[str, Ruleset[object]] = {}
bake_agents_on_restart = False
folder_attributes: dict[str, FolderAttributes] = {}

# BEGIN Kept for compatibility, but are deprecated and not used anymore
extra_summary_host_conf: dict = {}
extra_summary_service_conf: dict = {}
summary_host_groups: list = []
# service groups for aggregated services
summary_service_groups: list = []
# service contact groups for aggregated services
summary_service_contactgroups: list = []
summary_host_notification_periods: list = []
summary_service_notification_periods: list = []
service_aggregations: list = []
non_aggregated_hosts: list = []
aggregate_check_mk = False
aggregation_output_format = "multiline"  # new in 1.1.6. Possible also: "multiline"
aggr_summary_hostname = "%s-s"
legacy_checks: Ruleset[object] = []
# END Kept for compatibility

status_data_inventory: Ruleset[object] = []
logwatch_rules: Ruleset[object] = []
config_storage_format: Literal["standard", "raw", "pickle"] = "pickle"

automatic_host_removal: Ruleset[object] = []
