#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any as _Any
from typing import Dict as _Dict
from typing import Final as _Final
from typing import List as _List
from typing import Literal as _Literal
from typing import Optional as _Optional

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
_ALL_HOSTS: _Final = ["@all"]  # physical and cluster hosts
_NEGATE: _Final = "@negate"  # negation in boolean lists

monitoring_core: _Literal["nagios", "cmc"] = "nagios"
mkeventd_enabled = False  # Set by OMD hook
pnp4nagios_enabled = True  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports: Ruleset = []
agent_encryption: Ruleset = []
agent_exclude_sections: Ruleset = []
# UDP ports used for SNMP
snmp_ports: Ruleset = []
tcp_connect_timeout = 5.0
tcp_connect_timeouts: Ruleset = []
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking: _Optional[_Literal["abort", "wait"]] = "abort"
check_submission: _Literal["file", "pipe"] = "file"
default_host_group = "check_mk"

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
# Ruleset for translating piggyback host names
piggyback_translation: Ruleset = []
# Ruleset for translating service descriptions
service_description_translation: Ruleset = []
simulation_mode = False
fake_dns: _Optional[str] = None
agent_simulator = False
perfdata_format: _Literal["pnp", "standard"] = "pnp"
check_mk_perfdata_with_times = True
# TODO: Remove these options?
debug_log = False  # deprecated
monitoring_host: _Optional[str] = None  # deprecated
max_num_processes = 50
fallback_agent_output_encoding = "latin-1"
stored_passwords: _Dict[str, Password] = {}
# Collection of predefined rule conditions. For the moment this setting is only stored
# in this config domain but not used by the base code. The WATO logic for writing out
# rule.mk files is resolving the predefined conditions.
predefined_conditions: _Dict = {}
# Global setting for managing HTTP proxy configs
http_proxies: dict[str, dict[str, str]] = {}

# SNMP communities and encoding

# Global config for SNMP Backend
snmp_backend_default: _Literal["inline", "classic"] = "inline"
# Deprecated: Replaced by snmp_backend_hosts
use_inline_snmp: bool = True

# Ruleset to enable specific SNMP Backend for each host.
snmp_backend_hosts: Ruleset = []
# Deprecated: Replaced by snmp_backend_hosts
non_inline_snmp_hosts: Ruleset = []

# Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_limit_oid_range: Ruleset = []
# Ruleset to customize bulk size
snmp_bulk_size: Ruleset = []
snmp_default_community = "public"
snmp_communities: Ruleset = []
# override the rule based configuration
explicit_snmp_communities: _Dict[HostName, SNMPCredentials] = {}
snmp_timing: Ruleset = []
snmp_character_encodings: Ruleset = []

# Custom variables
explicit_service_custom_variables: dict[tuple[HostName, ServiceName], dict[str, str]] = {}

# Management board settings
# Ruleset to specify management board settings
management_board_config: Ruleset = []
# Mapping from hostname to management board protocol
management_protocol: dict[HostName, _Literal["snmp", "ipmi"]] = {}
# Mapping from hostname to SNMP credentials
management_snmp_credentials: dict[HostName, SNMPCredentials] = {}
# Mapping from hostname to IPMI credentials
management_ipmi_credentials: dict[HostName, dict[str, str]] = {}
# Ruleset to specify whether or not to use bulkwalk
management_bulkwalk_hosts: Ruleset = []

# RRD creation (only with CMC)
cmc_log_rrdcreation: _Optional[_Literal["terse", "full"]] = None
# Rule for per-host configuration of RRDs
cmc_host_rrd_config: Ruleset = []
# Rule for per-service configuration of RRDs
cmc_service_rrd_config: Ruleset = []

# Inventory and inventory checks
inventory_check_interval: _Optional[int] = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
inv_retention_intervals: Ruleset = []
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration

periodic_discovery: Ruleset = []

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
checks: Ruleset = []
static_checks: dict[str, Ruleset] = {}
check_parameters: Ruleset = []
checkgroup_parameters: dict[str, Ruleset] = {}
# for HW/SW-Inventory
inv_parameters: dict[str, Ruleset] = {}
# WATO variant for fully formalized checks
active_checks: dict[str, Ruleset] = {}
# WATO variant for datasource_programs
special_agents: dict[str, Ruleset] = {}
# WATO variant for free-form custom checks without formalization
custom_checks: Ruleset = []
all_hosts: _List = []
# store host tag config per host
host_tags: TagsOfHosts = {}
# store explicit host labels per host
host_labels: dict[HostName, Labels] = {}
# Assign labels via ruleset to hosts
host_label_rules: Ruleset = []
# Asssing labels via ruleset to services
service_label_rules: Ruleset = []
# TODO: This is a derived variable. Should be handled like others
# (hosttags, service_service_levels, ...)
# Map of hostnames to .mk files declaring the hosts (e.g. /wato/hosts.mk)
host_paths: dict[HostName, str] = {}
snmp_hosts: _List = [
    (["snmp"], _ALL_HOSTS),
]
tcp_hosts: _List = [
    (["tcp"], _ALL_HOSTS),
    (_NEGATE, ["snmp"], _ALL_HOSTS),
    # Match all those that don't have ping and don't have no-agent set
    (["!ping", "!no-agent"], _ALL_HOSTS),
]
cmk_agent_connection: dict[HostName, _Literal["pull-agent", "push-agent"]] = {}
bulkwalk_hosts: Ruleset = []
snmpv2c_hosts: Ruleset = []
snmp_without_sys_descr: Ruleset = []
snmpv3_contexts: Ruleset = []
usewalk_hosts: Ruleset = []
# use host name as ip address for these hosts
dyndns_hosts: Ruleset = []
primary_address_family: Ruleset = []
# exclude from inventory
ignored_checktypes: list[str] = []
# exclude from inventory
ignored_services: Ruleset = []
# exclude from inventory
ignored_checks: Ruleset = []
host_groups: Ruleset = []
service_groups: Ruleset = []
service_contactgroups: Ruleset = []
# deprecated, will be removed soon.
service_notification_periods: Ruleset = []
# deprecated, will be removed soon.
host_notification_periods: Ruleset = []
host_contactgroups: Ruleset = []
parents: Ruleset = []
define_hostgroups: _Dict[HostgroupName, str] = {}
define_servicegroups: _Dict[ServicegroupName, str] = {}
define_contactgroups: _Dict[ContactgroupName, str] = {}
contactgroup_members: _Dict[ContactgroupName, _List[ContactName]] = {}
contacts: dict[ContactName, Contact] = {}
# needed for WATO
timeperiods: TimeperiodSpecs = {}
clusters: dict[HostName, list[HostName]] = {}
clustered_services: Ruleset = []
# new in 1.1.4
clustered_services_of: _Dict = {}
# new for 1.2.5i1 Wato Rule
clustered_services_mapping: Ruleset = []
clustered_services_configuration: Ruleset = []
datasource_programs: Ruleset = []
service_dependencies: _List = []
# mapping from hostname to IPv4 address
ipaddresses: dict[HostName, HostAddress] = {}
# mapping from hostname to IPv6 address
ipv6addresses: dict[HostName, HostAddress] = {}
# mapping from hostname to addtional IPv4 addresses
additional_ipv4addresses: dict[HostName, list[HostAddress]] = {}
# mapping from hostname to addtional IPv6 addresses
additional_ipv6addresses: dict[HostName, list[HostAddress]] = {}
only_hosts: _Optional[Ruleset] = None
distributed_wato_site: _Optional[str] = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf: dict[str, Ruleset] = {}
explicit_host_conf: dict[str, dict[HostName, str]] = {}
extra_service_conf: dict[str, Ruleset] = {}
extra_nagios_conf = ""
service_descriptions: dict[str, str] = {}
# needed by WATO, ignored by Checkmk
host_attributes: dict[HostName, dict[str, _Any]] = {}
# special parameters for host/PING check_command
ping_levels: Ruleset = []
# alternative host check instead of check_icmp
host_check_commands: Ruleset = []
# time settings for piggybacked hosts
piggybacked_host_files: Ruleset = []
# Rule for specifying CMK's exit status in case of various errors
check_mk_exit_status: Ruleset = []
# Rule for defining expected version for agents
check_mk_agent_target_versions: Ruleset = []
check_periods: Ruleset = []
snmp_check_interval: Ruleset = []
snmp_exclude_sections: Ruleset = []
# Rulesets for parameters of notification scripts
notification_parameters: dict[str, Ruleset] = {}
use_new_descriptions_for: list[CheckPluginNameStr] = []
# Custom user icons / actions to be configured
host_icons_and_actions: Ruleset = []
# Custom user icons / actions to be configured
service_icons_and_actions: Ruleset = []
# Match all ruleset to assign custom service attributes
custom_service_attributes: Ruleset = []
# Assign tags to services
service_tag_rules: Ruleset = []

# Rulesets for agent bakery
agent_config: dict[str, Ruleset] = {}
bake_agents_on_restart = False
folder_attributes: dict[str, FolderAttributes] = {}

# BEGIN Kept for compatibility, but are deprecated and not used anymore
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
legacy_checks: Ruleset = []
# END Kept for compatibility

status_data_inventory: Ruleset = []
logwatch_rules: Ruleset = []
config_storage_format: _Literal["standard", "raw", "pickle"] = "pickle"
