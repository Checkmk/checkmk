#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import dataclasses
from collections.abc import Container, Mapping, Sequence
from typing import (
    Any,
    Literal,
)

import cmk.utils
import cmk.utils.tags
from cmk.base.default_config.cmc import (
    CMCAuthorization,
    CMCGraphiteConnection,
    CMCInitialScheduling,
    LogCmkHelpers,
    RealTimeChecks,
    SmartPingTuning,
)
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers import IPMICredentials
from cmk.checkengine.snmplib import SNMPCredentials, SNMPTiming
from cmk.inventory.structured_data import RawIntervalFromConfig
from cmk.rrd import RRDObjectConfig
from cmk.utils.host_storage import FolderAttributesForBase
from cmk.utils.http_proxy_config import HTTPProxySpec
from cmk.utils.labels import Labels
from cmk.utils.notify_types import (
    Contact,
    ContactName,
    EventRule,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotifyPluginParamsDict,
)
from cmk.utils.oauth2_connection import OAuth2Connection
from cmk.utils.rulesets import ruleset_matcher
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.servicename import ServiceName


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseConfig:
    """Typed snapshot of the loaded base configuration.

    The config loading still goes through module globals in `cmk.base.config`,
    but every value that is exposed here is meant to be accessed exclusively
    through this dataclass: direct `cmk.base.config.<X>` lookups for fields
    listed below have been migrated away. New base-config fields should land
    here (or on a scoped wrapper such as `CMCConfig` / `NagiosCoreConfig` /
    `NotificationConfig`) rather than as additional module globals.
    """

    # TODO: get `HostAddress` VS. `str` right! Which is it at what point?!
    # NOTE: all of the below is wishful typing, no parsing is done yet.
    # for now we just copy what we find in default_config
    folder_attributes: Mapping[str, FolderAttributesForBase]
    discovery_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    checkgroup_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    logwatch_rules: Sequence[RuleSpec[object]]
    static_checks: Mapping[
        str, list[RuleSpec[list[object]]]
    ]  # a.k.a. "enforced_services". Keep the name for consistency
    service_descriptions: Mapping[str, str]
    service_description_translation: Sequence[RuleSpec[Mapping[str, object]]]
    use_new_descriptions_for: Mapping[str, bool]
    monitoring_core: Literal["nagios", "cmc"]
    nagios_illegal_chars: str
    cmc_illegal_chars: str
    all_hosts: Sequence[str]
    clusters: Mapping[HostAddress, Sequence[HostAddress]]
    shadow_hosts: dict[HostName, dict[str, Any]]
    service_dependencies: Sequence[tuple]
    fallback_agent_output_encoding: str
    agent_config: Mapping[str, Sequence[RuleSpec]]
    agent_port: int
    agent_ports: Sequence[RuleSpec[int]]
    tcp_connect_timeout: float
    tcp_connect_timeouts: Sequence[RuleSpec[float]]
    encryption_handling: Sequence[RuleSpec[Mapping[str, str]]]
    piggyback_translation: Sequence[RuleSpec[Mapping[str, object]]]
    piggybacked_host_files: Sequence[RuleSpec[Mapping[str, object]]]
    piggyback_max_cachefile_age: int
    agent_encryption: Sequence[RuleSpec[str | None]]
    agent_exclude_sections: Sequence[RuleSpec[dict[str, str]]]
    cmc_real_time_checks: RealTimeChecks | None
    snmp_check_interval: list[
        RuleSpec[
            tuple[list[str], tuple[Literal["cached"], float] | tuple[Literal["uncached"], None]]
        ]
    ]
    apply_bake_revision: bool
    bake_agents_on_restart: bool
    agent_bakery_logging: int | None
    is_distributed_setup_remote_site: bool
    simulation_mode: bool
    use_dns_cache: bool
    ipaddresses: Mapping[HostName, HostAddress]
    ipv6addresses: Mapping[HostName, HostAddress]
    inventory_check_interval: object
    fake_dns: str | None
    tag_config: cmk.utils.tags.TagConfigSpec
    host_tags: ruleset_matcher.TagsOfHosts
    cmc_log_rrdcreation: Literal["terse", "full"] | None
    cmc_host_rrd_config: Sequence[RuleSpec[Any]]
    cmc_statehist_cache: Mapping[str, object] | None
    cmc_timeperiod_horizon: int
    host_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]]
    cmc_flap_settings: tuple[float, float, float]
    cmc_host_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]]
    cmc_host_long_output_in_monitoring_history: Sequence[RuleSpec[bool]]
    host_state_translation: Sequence[RuleSpec[Mapping[str, object]]]
    cmc_smartping_settings: Sequence[RuleSpec[Mapping[str, float]]]
    cmc_service_rrd_config: Sequence[RuleSpec[RRDObjectConfig]]
    service_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]]
    cmc_service_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]]
    cmc_service_long_output_in_monitoring_history: Sequence[RuleSpec[bool]]
    service_state_translation: Sequence[RuleSpec[Mapping[str, object]]]
    cmc_check_timeout: int
    cmc_service_check_timeout: Sequence[RuleSpec[int]]
    cmc_graphite_host_metrics: Sequence[RuleSpec[Sequence[str]]]
    cmc_graphite_service_metrics: Sequence[RuleSpec[Sequence[str]]]
    cmc_influxdb_service_metrics: Sequence[RuleSpec[Mapping[str, object]]]
    cmc_log_levels: Mapping[str, int]
    cluster_max_cachefile_age: int
    http_proxies: Mapping[str, HTTPProxySpec]
    oauth2_connections: Mapping[str, OAuth2Connection]
    extra_service_conf: Mapping[str, Sequence[RuleSpec[object]]]
    extra_host_conf: Mapping[str, Sequence[RuleSpec[Any]]]
    host_attributes: Mapping[HostName, Mapping[str, Any]]
    management_protocol: Mapping[HostName, Literal["snmp", "ipmi"]]
    management_snmp_credentials: Mapping[HostName, SNMPCredentials]
    management_ipmi_credentials: Mapping[HostName, IPMICredentials]
    snmp_default_community: str
    snmp_communities: Sequence[RuleSpec[SNMPCredentials]]
    inventory_check_severity: int
    enable_rulebased_notifications: bool
    current_customer: str
    host_paths: Mapping[HostName, str]
    timeperiods: object  # Here we don't lie for a change. We haven't parsed anything.
    check_periods: Sequence[RuleSpec[object]]
    relays: object  # see above
    cmc_config_multiprocessing: object
    cmc_check_helpers: int
    cmc_fetcher_helpers: int
    cmc_checker_helpers: int
    cmc_real_time_helpers: int
    cmc_initial_scheduling: CMCInitialScheduling
    cmc_housekeeping_interval: int
    cmc_state_retention_interval: int
    cmc_debug_notifications: bool
    cmc_dump_core: bool
    cmc_log_microtime: bool
    cmc_log_rotation_method: int
    cmc_log_limit: int
    cmc_log_cmk_helpers: LogCmkHelpers
    cmc_livestatus_threads: int
    cmc_max_response_size: int
    cmc_livestatus_logcache_size: int
    cmc_livestatus_lines_per_file: int
    cmc_authorization: CMCAuthorization
    cmc_smartping_check_interval: int
    cmc_smartping_tuning: SmartPingTuning
    mkeventd_enabled: bool
    pnp4nagios_enabled: bool
    cmc_pnp_update_delay: int
    cmc_pnp_update_on_restart: bool
    max_long_output_size: int
    influxdb_connections: Mapping[str, dict[str, Any]]
    cmc_graphite: Sequence[CMCGraphiteConnection]
    alert_handler_event_types: Sequence[Literal["statechange", "checkresult"]]
    alert_handler_rules: Sequence[EventRule]
    alert_handler_timeout: int
    alert_logging: int
    host_template: str
    cluster_template: str
    pingonly_template: str
    active_service_template: str
    passive_service_template_perf: str
    inventory_check_template: str
    service_dependency_template: str
    generate_hostconf: bool
    generate_dummy_commands: bool
    dummy_check_commandline: str
    delay_precompile: bool
    default_host_group: str
    extra_nagios_conf: str
    contacts: dict[ContactName, Contact]
    define_contactgroups: Mapping[str, str]
    define_hostgroups: Mapping[str, str]
    define_servicegroups: Mapping[str, str]
    contactgroup_members: Mapping[str, Sequence[ContactName]]
    cmc_import_nagios_state: bool
    restart_locking: Literal["abort", "wait"] | None
    check_submission: Literal["file", "pipe"]
    check_max_cachefile_age: int
    check_mk_perfdata_with_times: bool
    perfdata_format: Literal["pnp", "standard"]
    host_notification_periods: Sequence[RuleSpec[object]]
    service_notification_periods: Sequence[RuleSpec[object]]
    inventory_check_autotrigger: bool
    monitoring_host: str | None
    explicit_snmp_communities: Mapping[HostName | HostAddress, SNMPCredentials]
    cmc_host_limit: int | None
    cmc_service_limit: int | None
    cmc_store_params_in_config: bool
    notification_rules: Sequence[EventRule]
    notification_parameter: NotificationParameterSpecs
    notification_backlog: int
    notification_bulk_interval: int
    notification_fallback_email: str
    notification_fallback_format: tuple[NotificationPluginNameStr, NotifyPluginParamsDict]
    notification_plugin_timeout: int
    notification_logging: int
    notification_spooling: bool | Literal["local", "remote", "both", "off"] | None
    notification_spool_to: object
    active_checks: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    special_agents: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    custom_checks: Sequence[RuleSpec[dict[Any, Any]]]
    notification_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    inv_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    inv_retention_intervals: Sequence[RuleSpec[Sequence[RawIntervalFromConfig]]]
    periodic_discovery: Sequence[RuleSpec[Any]]
    check_mk_exit_status: Sequence[RuleSpec[Any]]
    ping_levels: Sequence[RuleSpec[Any]]
    primary_address_family: Sequence[RuleSpec[object]]
    datasource_programs: Sequence[RuleSpec[str]]
    only_hosts: Sequence[RuleSpec[bool]] | None
    distributed_wato_site: str | None
    dyndns_hosts: Sequence[RuleSpec[bool]]
    parents: Sequence[RuleSpec[str]]
    explicit_host_conf: Mapping[str, Mapping[HostName, Any]]
    host_label_rules: Sequence[RuleSpec[Mapping[str, str]]]
    service_label_rules: Sequence[RuleSpec[Mapping[str, str]]]
    host_labels: Mapping[HostName, Labels]
    host_groups: Sequence[RuleSpec[str]]
    host_contactgroups: Sequence[RuleSpec[str]]
    host_check_commands: Sequence[RuleSpec[str | tuple[str, int | str] | None]]
    host_icons_and_actions: Sequence[RuleSpec[str]]
    service_groups: Sequence[RuleSpec[str]]
    service_contactgroups: Sequence[RuleSpec[str]]
    service_icons_and_actions: Sequence[RuleSpec[str]]
    service_tag_rules: Sequence[RuleSpec[Sequence[tuple[str, str]]]]
    custom_service_attributes: Sequence[RuleSpec[Sequence[tuple[str, str]]]]
    explicit_service_custom_variables: dict[tuple[HostName, ServiceName], dict[str, str]]
    ignored_services: Sequence[RuleSpec[object]]
    ignored_checks: Sequence[RuleSpec[Container[str]]]
    clustered_services: Sequence[RuleSpec[object]]
    clustered_services_of: Mapping[HostAddress, Sequence[RuleSpec[object]]]
    clustered_services_mapping: Sequence[RuleSpec[HostAddress]]
    clustered_services_configuration: Sequence[
        RuleSpec[Sequence[Mapping[str, Mapping[object, object]]]]
    ]
    management_board_config: Sequence[RuleSpec[tuple[str, SNMPCredentials | IPMICredentials]]]
    snmp_ports: Sequence[RuleSpec[int]]
    snmp_timing: Sequence[RuleSpec[SNMPTiming]]
    snmp_bulk_size: Sequence[RuleSpec[int]]
    snmp_character_encodings: Sequence[RuleSpec[str | None]]
    snmp_backend_hosts: Sequence[RuleSpec[object]]
    snmp_backend_default: Literal["inline", "classic"]
    snmp_limit_oid_range: Sequence[RuleSpec[object]]
    snmp_exclude_sections: Sequence[RuleSpec[Mapping[str, Sequence[str]]]]
    snmp_without_sys_descr: Sequence[RuleSpec[bool]]
    snmpv2c_hosts: Sequence[RuleSpec[bool]]
    snmpv3_contexts: Sequence[
        RuleSpec[
            tuple[str | None, Sequence[str], Literal["continue_on_timeout", "stop_on_timeout"]]
        ]
    ]
    bulkwalk_hosts: Sequence[RuleSpec[bool]]
    management_bulkwalk_hosts: Sequence[RuleSpec[bool]]
    usewalk_hosts: Sequence[RuleSpec[bool]]
