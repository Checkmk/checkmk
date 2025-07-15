#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Iterable, Mapping, Sequence
from typing import Any, Final, Literal, SupportsInt, TypeAlias, TypedDict

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.host_storage import FolderAttributesForBase
from cmk.utils.labels import Labels
from cmk.utils.notify_types import Contact, ContactName
from cmk.utils.password_store import Password
from cmk.utils.rulesets.ruleset_matcher import RuleSpec, TagsOfHosts
from cmk.utils.servicename import ServiceName
from cmk.utils.structured_data import RawIntervalFromConfig
from cmk.utils.tags import TagConfigSpec
from cmk.utils.timeperiod import TimeperiodSpecs
from cmk.utils.translations import TranslationOptions, TranslationOptionsSpec

from cmk.snmplib import RangeLimit, SNMPCredentials, SNMPTiming

from cmk.fetchers import IPMICredentials

from cmk.checkengine.discovery import RediscoveryParameters
from cmk.checkengine.exitspec import ExitSpec

from cmk.server_side_calls_backend import ConfigSet as SSCConfigSet

# This file contains the defaults settings for almost all configuration
# variables that can be overridden in main.mk. Some configuration
# variables are preset in checks/* as well.

_ContactgroupName = str

# TODO: Remove the duplication with cmk.base.config
_ALL_HOSTS: Final = ["@all"]  # physical and cluster hosts
_NEGATE: Final = "@negate"  # negation in boolean lists
_HostgroupName: TypeAlias = str
_ServicegroupName: TypeAlias = str

monitoring_core: Literal["nagios", "cmc"] = "nagios"
mkeventd_enabled = False  # Set by OMD hook
pnp4nagios_enabled = True  # Set by OMD hook
# TODO: Is this one deprecated for a long time?
agent_port = 6556
agent_ports: list[RuleSpec[int]] = []
agent_encryption: list[RuleSpec[str | None]] = []
encryption_handling: list[RuleSpec[Mapping[str, str]]] = []
agent_exclude_sections: list[RuleSpec[dict[str, str]]] = []
# UDP ports used for SNMP
snmp_ports: list[RuleSpec[int]] = []
tcp_connect_timeout = 5.0
tcp_connect_timeouts: list[RuleSpec[float]] = []
use_dns_cache = True  # prevent DNS by using own cache file
delay_precompile = False  # delay Python compilation to Nagios execution
restart_locking: Literal["abort", "wait"] | None = "abort"
check_submission: Literal["file", "pipe"] = "file"
default_host_group = "check_mk"

check_max_cachefile_age = 0  # per default do not use cache files when checking
cluster_max_cachefile_age = 90  # secs.
piggyback_max_cachefile_age = 3600  # secs
# Ruleset for translating piggyback host names
piggyback_translation: list[RuleSpec[TranslationOptions]] = []
# Ruleset for translating service names
service_description_translation: list[RuleSpec[TranslationOptionsSpec]] = []
simulation_mode = False
fake_dns: str | None = None
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

# Ruleset to enable specific SNMP Backend for each host.
snmp_backend_hosts: list[RuleSpec[object]] = []
# Deprecated: Replaced by snmp_backend_hosts
non_inline_snmp_hosts: list[RuleSpec[object]] = []

# Ruleset to recduce fetched OIDs of a check, only inline SNMP
snmp_limit_oid_range: list[RuleSpec[tuple[str, Sequence[RangeLimit]]]] = []
# Ruleset to customize bulk size
snmp_bulk_size: list[RuleSpec[int]] = []
snmp_default_community = "public"
snmp_communities: list[RuleSpec[SNMPCredentials]] = []
# override the rule based configuration
explicit_snmp_communities: dict[HostName | HostAddress, SNMPCredentials] = {}
snmp_timing: list[RuleSpec[SNMPTiming]] = []
snmp_character_encodings: list[RuleSpec[str | None]] = []

# Custom variables
explicit_service_custom_variables: dict[tuple[HostName, ServiceName], dict[str, str]] = {}

# Management board settings
# Ruleset to specify management board settings
management_board_config: list[RuleSpec[tuple[str, SNMPCredentials | IPMICredentials]]] = []
# Mapping from hostname to management board protocol
management_protocol: dict[HostName, Literal["snmp", "ipmi"]] = {}
# Mapping from hostname to SNMP credentials
management_snmp_credentials: dict[HostName, SNMPCredentials] = {}
# Mapping from hostname to IPMI credentials
management_ipmi_credentials: dict[HostName, IPMICredentials] = {}
# Ruleset to specify whether or not to use bulkwalk
management_bulkwalk_hosts: list[RuleSpec[bool]] = []

# RRD creation (only with CMC)
cmc_log_rrdcreation: Literal["terse", "full"] | None = None
# Rule for per-host configuration of RRDs
cmc_host_rrd_config: list[RuleSpec[Any]] = []
# Rule for per-service configuration of RRDs


class _RRDConfig(TypedDict):
    """RRDConfig
    This typing might not be complete or even wrong, feel free to improve"""

    cfs: Iterable[Literal["MIN", "MAX", "AVERAGE"]]  # conceptually a Set[Literal[...]]
    rras: list[tuple[float, int, int]]
    step: int
    format: Literal["pnp_multiple", "cmc_single"]


cmc_service_rrd_config: list[RuleSpec[_RRDConfig]] = []

# Inventory and inventory checks
inventory_check_interval: int | None = None  # Nagios intervals (4h = 240)
inventory_check_severity = 1  # warning
inventory_max_cachefile_age = 120  # seconds
inventory_check_autotrigger = True  # Automatically trigger inv-check after automation-inventory
inv_retention_intervals: list[RuleSpec[Sequence[RawIntervalFromConfig]]] = []
# TODO: Remove this already deprecated option
always_cleanup_autochecks = None  # For compatiblity with old configuration


class _PeriodicDiscovery(TypedDict):
    severity_unmonitored: SupportsInt
    severity_vanished: SupportsInt
    severity_changed_service_labels: SupportsInt
    severity_changed_service_params: SupportsInt
    severity_new_host_label: SupportsInt
    check_interval: SupportsInt
    inventory_rediscovery: RediscoveryParameters


periodic_discovery: list[RuleSpec[_PeriodicDiscovery]] = []

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
static_checks: dict[str, list[RuleSpec[list[object]]]] = {}
checkgroup_parameters: dict[str, list[RuleSpec[Mapping[str, object]]]] = {}
# for HW/SW Inventory
inv_parameters: dict[str, list[RuleSpec[Mapping[str, object]]]] = {}


# WATO variant for fully formalized checks / special agents.
# The typing here is a lie, we cannot know what customers have configred (in the past)
# There's a parsing step later that ensures this.
active_checks: dict[str, list[RuleSpec[SSCConfigSet]]] = {}
special_agents: dict[str, list[RuleSpec[SSCConfigSet]]] = {}


# WATO variant for free-form custom checks without formalization
custom_checks: list[RuleSpec[dict[Any, Any]]] = []
all_hosts: list = []
# store host tag config per host
host_tags: TagsOfHosts = {}
# store explicit host labels per host
host_labels: dict[HostName, Labels] = {}
# Assign labels via ruleset to hosts
host_label_rules: list[RuleSpec[Mapping[str, str]]] = []
# Asssing labels via ruleset to services
service_label_rules: list[RuleSpec[Mapping[str, str]]] = []
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
# cf. cmk.checkengine.checking.HostAgentConnectionMode, currently there seems to be no good way to
# directly couple these two definitions
# https://github.com/python/typing/issues/781
cmk_agent_connection: dict[HostName, Literal["pull-agent", "push-agent"]] = {}
bulkwalk_hosts: list[RuleSpec[bool]] = []
snmpv2c_hosts: list[RuleSpec[bool]] = []
snmp_without_sys_descr: list[RuleSpec[bool]] = []
snmpv3_contexts: list[
    RuleSpec[tuple[str | None, Sequence[str], Literal["continue_on_timeout", "stop_on_timeout"]]]
] = []
usewalk_hosts: list[RuleSpec[bool]] = []
# use host name as ip address for these hosts
dyndns_hosts: list[RuleSpec[bool]] = []
primary_address_family: list[RuleSpec[object]] = []
# exclude from inventory
ignored_checktypes: list[str] = []
# exclude from inventory
ignored_services: list[RuleSpec[object]] = []
# exclude from inventory
ignored_checks: list[RuleSpec[Container[str]]] = []
host_groups: list[RuleSpec[str]] = []
service_groups: list[RuleSpec[str]] = []
service_contactgroups: list[RuleSpec[str]] = []
# deprecated, will be removed soon.
service_notification_periods: list[RuleSpec[object]] = []
# deprecated, will be removed soon.
host_notification_periods: list[RuleSpec[object]] = []
host_contactgroups: list[RuleSpec[str]] = []
parents: list[RuleSpec[str]] = []
define_hostgroups: dict[_HostgroupName, str] = {}
define_servicegroups: dict[_ServicegroupName, str] = {}
define_contactgroups: dict[_ContactgroupName, str] = {}
contactgroup_members: dict[_ContactgroupName, list[ContactName]] = {}
contacts: dict[ContactName, Contact] = {}
# needed for WATO
timeperiods: TimeperiodSpecs = {}
clusters: dict[HostName, list[HostName]] = {}
clustered_services: list[RuleSpec[object]] = []
# new in 1.1.4
clustered_services_of: dict[HostAddress, Sequence[RuleSpec[object]]] = {}
# new for 1.2.5i1 Wato Rule
clustered_services_mapping: list[RuleSpec[HostAddress]] = []
clustered_services_configuration: list[
    RuleSpec[Sequence[Mapping[str, Mapping[object, object]]]]
] = []
datasource_programs: list[RuleSpec[str]] = []
service_dependencies: list = []
# mapping from hostname to IPv4 address
ipaddresses: dict[HostName | HostAddress, HostAddress] = {}
# mapping from hostname to IPv6 address
ipv6addresses: dict[HostName | HostAddress, HostAddress] = {}
# mapping from hostname to addtional IPv4 addresses
additional_ipv4addresses: dict[HostName, list[HostAddress]] = {}
# mapping from hostname to addtional IPv6 addresses
additional_ipv6addresses: dict[HostName, list[HostAddress]] = {}
only_hosts: list[RuleSpec[bool]] | None = None
distributed_wato_site: str | None = None  # used by distributed WATO
is_wato_slave_site = False
extra_host_conf: dict[str, list[RuleSpec[Any]]] = {}
explicit_host_conf: dict[str, dict[HostName, Any]] = {}
extra_service_conf: dict[str, list[RuleSpec[int]]] = {}
extra_nagios_conf = ""
service_descriptions: dict[str, str] = {}
# host_attributes store explicitly configured attributes in WATO
# and does not include inheritance from folders
host_attributes: dict[HostName, dict[str, Any]] = {}
# special parameters for host/PING check_command
_PingLevels = dict[str, int | tuple[float, float]]
ping_levels: list[RuleSpec[_PingLevels]] = []
# alternative host check instead of check_icmp
_HostCheckCommand = str | tuple[str, int | str] | None
host_check_commands: list[RuleSpec[_HostCheckCommand]] = []
# time settings for piggybacked hosts
piggybacked_host_files: list[RuleSpec[Mapping[str, object]]] = []
# Rule for specifying CMK's exit status in case of various errors


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: dict[str, ExitSpec]


check_mk_exit_status: list[RuleSpec[_NestedExitSpec]] = []
# Rule for defining expected version for agents
check_mk_agent_target_versions: list[RuleSpec[str]] = []
check_periods: list[RuleSpec[str]] = []
snmp_check_interval: list[
    RuleSpec[tuple[list[str], tuple[Literal["cached"], float] | tuple[Literal["uncached"], None]]]
] = []
snmp_exclude_sections: list[RuleSpec[Mapping[str, Sequence[str]]]] = []
# Rulesets for parameters of notification scripts
notification_parameters: dict[str, list[RuleSpec[Mapping[str, object]]]] = {}
use_new_descriptions_for: list[str] = []
# Custom user icons / actions to be configured
host_icons_and_actions: list[RuleSpec[str]] = []
# Custom user icons / actions to be configured
service_icons_and_actions: list[RuleSpec[str]] = []
# Match all ruleset to assign custom service attributes
custom_service_attributes: list[RuleSpec[Sequence[tuple[str, str]]]] = []
# Assign tags to services
service_tag_rules: list[RuleSpec[Sequence[tuple[str, str]]]] = []

# Rulesets for Agent Bakery
agent_config: dict[str, list[RuleSpec[Any]]] = {}
agent_bakery_logging: int | None = None
bake_agents_on_restart = False
apply_bake_revision = False
folder_attributes: dict[str, FolderAttributesForBase] = {}

# BEGIN Kept for compatibility, but are deprecated and not used anymore
inv_exports: dict = {}  # Rulesets for inventory export hooks
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
# END Kept for compatibility

status_data_inventory: list[RuleSpec[object]] = []
logwatch_rules: list[RuleSpec[object]] = []
config_storage_format: Literal["standard", "raw", "pickle"] = "pickle"

automatic_host_removal: list[RuleSpec[object]] = []
