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
from cmk.base.configlib.cmc import CMCConfigFields
from cmk.base.configlib.notify import AlertHandlingConfigFields, NotifyConfigFields
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers.ipmi import IPMICredentials
from cmk.checkengine.snmplib import SNMPCredentials, SNMPTiming
from cmk.events.notify_types import (
    Contact,
    ContactName,
)
from cmk.inventory.label_picker import LabelPickerRuleValue
from cmk.inventory.trees import RawIntervalFromConfig
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


# BaseConfig is composed of field groups (the ones below, and those in
# .cmc and .notify) that mirror the split of the former
# cmk.base.default_config package. One day, the consumers should only
# parse what they actually need, rather than all of BaseConfig.


@dataclasses.dataclass(frozen=True, kw_only=True)
class _CustomerConfig:
    current_customer: str = "provider"


@dataclasses.dataclass(frozen=True, kw_only=True)
class _RelayConfig:
    relays: object = dataclasses.field(default_factory=dict)  # not parsed


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseConfig(  # type: ignore[explicit-any]
    AlertHandlingConfigFields,
    CMCConfigFields,
    _CustomerConfig,
    NotifyConfigFields,
    _RelayConfig,
):
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
    telemetry_custom_service: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    metrics_identity_routing: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
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
    host_paths: Mapping[HostName, str] = dataclasses.field(default_factory=dict)
    timeperiods: object = dataclasses.field(
        default_factory=dict
    )  # Here we don't lie for a change. We haven't parsed anything.
    check_periods: Sequence[RuleSpec[object]] = dataclasses.field(default_factory=list)
    mkeventd_enabled: bool = False
    pnp4nagios_enabled: bool = True
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
    active_checks: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = dataclasses.field(
        default_factory=dict
    )
    special_agents: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]] = dataclasses.field(
        default_factory=dict
    )
    custom_checks: Sequence[RuleSpec[CustomCheck]] = dataclasses.field(default_factory=list)
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
