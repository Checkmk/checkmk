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
    NotRequired,
    ReadOnly,
    TypedDict,
)

import cmk.ruleset_matcher.tags
from cmk.base.default_config.cmc import (
    CMCAuthorization,
    CMCGraphiteConnection,
    CMCInitialScheduling,
    LogCmkHelpers,
    RealTimeChecks,
    SmartPingTuning,
)
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers.ipmi import IPMICredentials
from cmk.checkengine.snmplib import SNMPCredentials, SNMPTiming
from cmk.events.notify_types import (
    Contact,
    ContactName,
    EventRule,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    NotifyPluginParamsDict,
)
from cmk.inventory.label_picker import LabelPickerRuleValue
from cmk.inventory.trees import RawIntervalFromConfig
from cmk.rrd import RRDObjectConfig
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.matcher import RuleSpec
from cmk.utils.host_storage import FolderAttributesForBase
from cmk.utils.http_proxy_config import HTTPProxySpec
from cmk.utils.oauth2_connection import OAuth2Connection
from cmk.utils.servicename import ServiceName


class CustomCheckFreshness(TypedDict):
    interval: ReadOnly[int]
    state: ReadOnly[int]
    output: ReadOnly[str]


class CustomCheck(TypedDict):
    """A rule value of the "Integrate Nagios plug-ins" ruleset."""

    service_description: ReadOnly[str]
    command_line: NotRequired[ReadOnly[str]]
    command_name: NotRequired[ReadOnly[str]]
    freshness: NotRequired[ReadOnly[CustomCheckFreshness]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseConfig:  # type: ignore[explicit-any]
    """Typed snapshot of the loaded base configuration.

    The config loader (`load()` / `load_packed_config()`) builds an instance
    of this class from a local namespace dict; `cmk.base.config.__dict__`
    is not mutated. Every value exposed here is accessed exclusively
    through this dataclass: direct `cmk.base.config.<X>` lookups for
    fields listed below have been migrated away. New base-config fields
    should land here (or on a scoped wrapper such as `CMCConfig` /
    `NagiosCoreConfig` / `NotificationConfig`) rather than as additional
    module globals.
    """

    # TODO: get `HostAddress` VS. `str` right! Which is it at what point?!
    # NOTE: all of the below is wishful typing, no parsing is done yet.
    # for now we just copy what we find in default_config
    folder_attributes: Mapping[str, FolderAttributesForBase] = dataclasses.field(
        default_factory=dict
    )
    discovery_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = (
        dataclasses.field(default_factory=dict)
    )
    checkgroup_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = (
        dataclasses.field(default_factory=dict)
    )
    logwatch_rules: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    static_checks: Mapping[str, list[RuleSpec[list[object]]]] = dataclasses.field(
        default_factory=dict
    )  # a.k.a. "enforced_services". Keep the name for consistency
    service_descriptions: Mapping[str, str] = dataclasses.field(default_factory=dict)
    service_description_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    use_new_descriptions_for: Mapping[str, bool] = dataclasses.field(default_factory=dict)
    monitoring_core: Literal["nagios", "cmc"] = "nagios"
    nagios_illegal_chars: str = "`;~!$%^&*|'\"<>?,="
    cmc_illegal_chars: str = ";\t"
    all_hosts: Sequence[str] = dataclasses.field(default_factory=list)
    clusters: Mapping[HostAddress, Sequence[HostAddress]] = dataclasses.field(default_factory=dict)
    shadow_hosts: dict[HostName, dict[str, object]] = dataclasses.field(default_factory=dict)
    service_dependencies: Sequence[tuple] = dataclasses.field(default_factory=list)
    fallback_agent_output_encoding: str = "latin-1"
    agent_config: Mapping[str, Sequence[RuleSpec]] = dataclasses.field(default_factory=dict)
    agent_port: int = 6556
    agent_ports: Sequence[RuleSpec[int]] = dataclasses.field(default_factory=list)
    tcp_connect_timeout: float = 5.0
    tcp_connect_timeouts: Sequence[RuleSpec[float]] = dataclasses.field(default_factory=list)
    encryption_handling: Sequence[RuleSpec[Mapping[str, str]]] = dataclasses.field(
        default_factory=list
    )
    piggyback_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    piggybacked_host_files: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    piggyback_max_cachefile_age: int = 3600
    agent_encryption: Sequence[RuleSpec[str | None]] = dataclasses.field(default_factory=list)
    agent_exclude_sections: Sequence[RuleSpec[dict[str, str]]] = dataclasses.field(
        default_factory=list
    )
    telemetry_custom_service: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    metrics_identity_routing: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    cmc_real_time_checks: RealTimeChecks | None = None
    snmp_check_interval: list[
        RuleSpec[
            tuple[list[str], tuple[Literal["cached"], float] | tuple[Literal["uncached"], None]]
        ]
    ] = dataclasses.field(default_factory=list)
    apply_bake_revision: bool = False
    agent_bakery_logging: int | None = None
    is_distributed_setup_remote_site: bool = False
    simulation_mode: bool = False
    use_dns_cache: bool = True
    ipaddresses: Mapping[HostName, HostAddress] = dataclasses.field(default_factory=dict)
    ipv6addresses: Mapping[HostName, HostAddress] = dataclasses.field(default_factory=dict)
    inventory_check_interval: object = None
    fake_dns: str | None = None
    tag_config: cmk.ruleset_matcher.tags.TagConfigSpec = dataclasses.field(
        default_factory=lambda: cmk.ruleset_matcher.tags.TagConfigSpec(tag_groups=[], aux_tags=[])
    )
    host_tags: object = dataclasses.field(default_factory=dict)
    cmc_log_rrdcreation: Literal["terse", "full"] | None = None
    cmc_host_rrd_config: Sequence[RuleSpec[Any]] = dataclasses.field(default_factory=list)
    cmc_statehist_cache: Mapping[str, object] | None = dataclasses.field(
        default_factory=lambda: {"horizon": 63072000, "max_core_downtime": 30}
    )
    cmc_timeperiod_horizon: int = 2 * 365
    host_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_flap_settings: tuple[float, float, float] = (3.0, 5.0, 0.1)
    cmc_host_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_host_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = dataclasses.field(
        default_factory=list
    )
    host_state_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    cmc_smartping_settings: Sequence[RuleSpec[Mapping[str, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_service_rrd_config: Sequence[RuleSpec[RRDObjectConfig]] = dataclasses.field(
        default_factory=list
    )
    service_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_service_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_service_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = dataclasses.field(
        default_factory=list
    )
    service_state_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    cmc_check_timeout: int = 60
    cmc_service_check_timeout: Sequence[RuleSpec[int]] = dataclasses.field(default_factory=list)
    cmc_graphite_host_metrics: Sequence[RuleSpec[Sequence[str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_graphite_service_metrics: Sequence[RuleSpec[Sequence[str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_influxdb_service_metrics: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    cmc_log_levels: Mapping[str, int] = dataclasses.field(
        default_factory=lambda: {
            "cmk.alert": 5,
            "cmk.carbon": 5,
            "cmk.core": 5,
            "cmk.downtime": 5,
            "cmk.helper": 5,
            "cmk.livestatus": 5,
            "cmk.notification": 5,
            "cmk.rrd": 5,
            "cmk.influxdb": 5,
            "cmk.smartping": 5,
        }
    )
    cluster_max_cachefile_age: int = 90
    http_proxies: Mapping[str, HTTPProxySpec] = dataclasses.field(default_factory=dict)
    oauth2_connections: Mapping[str, OAuth2Connection] = dataclasses.field(default_factory=dict)
    extra_service_conf: Mapping[str, Sequence[RuleSpec[object]]] = dataclasses.field(
        default_factory=dict
    )
    extra_host_conf: Mapping[str, Sequence[RuleSpec[Any]]] = dataclasses.field(default_factory=dict)
    host_attributes: Mapping[HostName, Mapping[str, Any]] = dataclasses.field(default_factory=dict)  # type: ignore[explicit-any]
    management_protocol: Mapping[HostName, Literal["snmp", "ipmi"]] = dataclasses.field(
        default_factory=dict
    )
    management_snmp_credentials: Mapping[HostName, SNMPCredentials] = dataclasses.field(
        default_factory=dict
    )
    management_ipmi_credentials: Mapping[HostName, IPMICredentials] = dataclasses.field(
        default_factory=dict
    )
    snmp_default_community: str = "public"
    snmp_communities: Sequence[RuleSpec[SNMPCredentials]] = dataclasses.field(default_factory=list)
    inventory_check_severity: int = 1
    enable_rulebased_notifications: bool = True
    current_customer: str = "provider"
    host_paths: Mapping[HostName, str] = dataclasses.field(default_factory=dict)
    timeperiods: object = dataclasses.field(
        default_factory=dict
    )  # Here we don't lie for a change. We haven't parsed anything.
    check_periods: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    relays: object = dataclasses.field(default_factory=dict)  # see above
    cmc_config_multiprocessing: object = dataclasses.field(
        default_factory=lambda: {"use_multiprocessing": True}
    )
    cmc_check_helpers: int = 5
    cmc_fetcher_helpers: int = 13
    cmc_checker_helpers: int = 4
    cmc_real_time_helpers: int = 1
    cmc_initial_scheduling: CMCInitialScheduling = dataclasses.field(
        default_factory=lambda: CMCInitialScheduling(burst=10, spread_cmk=1200, spread_generic=150)
    )
    cmc_housekeeping_interval: int = 1000
    cmc_state_retention_interval: int = 600
    cmc_debug_notifications: bool = False
    cmc_dump_core: bool = False
    cmc_log_microtime: bool = False
    cmc_log_rotation_method: int = 3
    cmc_log_limit: int = 50 * 1024 * 1024
    cmc_log_cmk_helpers: LogCmkHelpers = dataclasses.field(
        default_factory=lambda: LogCmkHelpers(log_level=0, debug=False)
    )
    cmc_livestatus_threads: int = 20
    cmc_max_response_size: int = 100
    cmc_livestatus_logcache_size: int = 500000
    cmc_livestatus_lines_per_file: int = 1000000
    cmc_authorization: CMCAuthorization = dataclasses.field(
        default_factory=lambda: CMCAuthorization(host=0, group=0)
    )
    cmc_smartping_check_interval: int = 500
    cmc_smartping_tuning: SmartPingTuning = dataclasses.field(
        default_factory=lambda: SmartPingTuning(omit_payload=False, num_sockets=8, ignore_rst=False)
    )
    mkeventd_enabled: bool = False
    pnp4nagios_enabled: bool = True
    cmc_pnp_update_delay: int = 3600
    cmc_pnp_update_on_restart: bool = False
    max_long_output_size: int = 2000
    influxdb_connections: Mapping[str, dict[str, object]] = dataclasses.field(default_factory=dict)
    cmc_graphite: Sequence[CMCGraphiteConnection] = dataclasses.field(default_factory=list)
    alert_handler_event_types: Sequence[Literal["statechange", "checkresult"]] = dataclasses.field(
        default_factory=lambda: ["statechange"]
    )
    alert_handler_rules: Sequence[EventRule] = dataclasses.field(default_factory=list)
    alert_handler_timeout: int = 60
    alert_logging: int = 20
    host_template: str = "check_mk_host"
    cluster_template: str = "check_mk_cluster"
    pingonly_template: str = "check_mk_pingonly"
    active_service_template: str = "check_mk_active"
    passive_service_template_perf: str = "check_mk_passive_perf"
    inventory_check_template: str = "check_mk_inventory"
    service_dependency_template: str = "check_mk"
    generate_hostconf: bool = True
    generate_dummy_commands: bool = True
    dummy_check_commandline: str = (
        'echo "ERROR - you did an active check on this service - please disable active checks" '
        "&& exit 1"
    )
    delay_precompile: bool = False
    default_host_group: str = "check_mk"
    extra_nagios_conf: str = ""
    contacts: Mapping[ContactName, Contact] = dataclasses.field(default_factory=dict)
    define_contactgroups: Mapping[str, str] = dataclasses.field(default_factory=dict)
    define_hostgroups: Mapping[str, str] = dataclasses.field(default_factory=dict)
    define_servicegroups: Mapping[str, str] = dataclasses.field(default_factory=dict)
    contactgroup_members: Mapping[str, Sequence[ContactName]] = dataclasses.field(
        default_factory=dict
    )
    cmc_import_nagios_state: bool = True
    restart_locking: Literal["abort", "wait"] | None = "abort"
    check_submission: Literal["file", "pipe"] = "file"
    check_max_cachefile_age: int = 0
    check_mk_perfdata_with_times: bool = True
    perfdata_format: Literal["pnp", "standard"] = "pnp"
    host_notification_periods: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    service_notification_periods: Sequence[RuleSpec[object]] = dataclasses.field(
        default_factory=list
    )
    inventory_check_autotrigger: bool = True
    monitoring_host: str | None = None
    explicit_snmp_communities: Mapping[HostName | HostAddress, SNMPCredentials] = dataclasses.field(
        default_factory=dict
    )
    cmc_host_limit: int | None = None
    cmc_service_limit: int | None = None
    cmc_store_params_in_config: bool = False
    notification_rules: Sequence[EventRule] = dataclasses.field(default_factory=list)
    notification_parameter: NotificationParameterSpecs = dataclasses.field(default_factory=dict)
    notification_backlog: int = 10
    notification_bulk_interval: int = 10
    notification_fallback_email: str = ""
    notification_fallback_format: tuple[NotificationPluginNameStr, NotifyPluginParamsDict] = (
        "asciimail",
        {},
    )
    notification_plugin_timeout: int = 60
    notification_logging: int = 15
    notification_spooling: bool | Literal["local", "remote", "both", "off"] | None = None
    notification_spool_to: object = None
    active_checks: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = dataclasses.field(
        default_factory=dict
    )
    special_agents: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = dataclasses.field(
        default_factory=dict
    )
    custom_checks: Sequence[RuleSpec[CustomCheck]] = dataclasses.field(default_factory=list)
    notification_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = (
        dataclasses.field(default_factory=dict)
    )
    inv_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = dataclasses.field(
        default_factory=dict
    )
    inv_retention_intervals: Sequence[RuleSpec[Sequence[RawIntervalFromConfig]]] = (
        dataclasses.field(default_factory=list)
    )
    inv_label_picker_configs: Sequence[RuleSpec[LabelPickerRuleValue]] = dataclasses.field(
        default_factory=list
    )
    periodic_discovery: Sequence[RuleSpec[Any]] = dataclasses.field(default_factory=list)
    check_mk_exit_status: Sequence[RuleSpec[Any]] = dataclasses.field(default_factory=list)
    ping_levels: Sequence[RuleSpec[Any]] = dataclasses.field(default_factory=list)
    primary_address_family: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    datasource_programs: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    only_hosts: Sequence[RuleSpec[bool]] | None = None
    distributed_wato_site: str | None = None
    dyndns_hosts: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
    parents: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    explicit_host_conf: Mapping[str, Mapping[HostName, object]] = dataclasses.field(
        default_factory=dict
    )
    host_label_rules: Sequence[RuleSpec[Mapping[str, str]]] = dataclasses.field(
        default_factory=list
    )
    service_label_rules: Sequence[RuleSpec[Mapping[str, str]]] = dataclasses.field(
        default_factory=list
    )
    host_labels: Mapping[HostName, Labels] = dataclasses.field(default_factory=dict)
    host_groups: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    host_contactgroups: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    host_check_commands: Sequence[RuleSpec[str | tuple[str, int | str] | None]] = dataclasses.field(
        default_factory=list
    )
    host_icons_and_actions: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    service_groups: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    service_contactgroups: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    service_icons_and_actions: Sequence[RuleSpec[str]] = dataclasses.field(default_factory=list)
    service_tag_rules: Sequence[RuleSpec[Sequence[tuple[str, str]]]] = dataclasses.field(
        default_factory=list
    )
    custom_service_attributes: Sequence[RuleSpec[Sequence[tuple[str, str]]]] = dataclasses.field(
        default_factory=list
    )
    explicit_service_custom_variables: dict[tuple[HostName, ServiceName], dict[str, str]] = (
        dataclasses.field(default_factory=dict)
    )
    ignored_services: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    ignored_checks: Sequence[RuleSpec[Container[str]]] = dataclasses.field(default_factory=list)
    clustered_services: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    clustered_services_of: Mapping[HostAddress, Sequence[RuleSpec[object]]] = dataclasses.field(
        default_factory=dict
    )
    clustered_services_mapping: Sequence[RuleSpec[HostAddress]] = dataclasses.field(
        default_factory=list
    )
    clustered_services_configuration: Sequence[
        RuleSpec[Sequence[Mapping[str, Mapping[object, object]]]]
    ] = dataclasses.field(default_factory=list)
    management_board_config: Sequence[RuleSpec[tuple[str, SNMPCredentials | IPMICredentials]]] = (
        dataclasses.field(default_factory=list)
    )
    snmp_ports: Sequence[RuleSpec[int]] = dataclasses.field(default_factory=list)
    snmp_timing: Sequence[RuleSpec[SNMPTiming]] = dataclasses.field(default_factory=list)
    snmp_bulk_size: Sequence[RuleSpec[int]] = dataclasses.field(default_factory=list)
    snmp_character_encodings: Sequence[RuleSpec[str | None]] = dataclasses.field(
        default_factory=list
    )
    snmp_backend_hosts: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    snmp_backend_default: Literal["inline", "classic"] = "classic"
    snmp_limit_oid_range: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    snmp_exclude_sections: Sequence[RuleSpec[Mapping[str, Sequence[str]]]] = dataclasses.field(
        default_factory=list
    )
    snmp_without_sys_descr: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
    snmpv2c_hosts: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
    snmpv3_contexts: Sequence[
        RuleSpec[
            tuple[str | None, Sequence[str], Literal["continue_on_timeout", "stop_on_timeout"]]
        ]
    ] = dataclasses.field(default_factory=list)
    bulkwalk_hosts: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
    management_bulkwalk_hosts: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
    usewalk_hosts: Sequence[RuleSpec[bool]] = dataclasses.field(default_factory=list)
