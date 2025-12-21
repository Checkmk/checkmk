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
from cmk.base.default_config.cmc import RealTimeChecks
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.rrd.config import RRDObjectConfig
from cmk.utils.host_storage import FolderAttributesForBase
from cmk.utils.http_proxy_config import HTTPProxySpec
from cmk.utils.oauth2_connection import OAuth2Connection
from cmk.utils.rulesets import ruleset_matcher, RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RuleSpec


@dataclasses.dataclass(frozen=True, kw_only=True)
class LoadedConfigFragment:
    """Return *some of* the values that have been loaded as part of the config loading process.

    The config loading currently mostly manipulates a global state.
    Return an instance of this class, to indicate that the config has been loaded.

    Someday (TM): return the actual loaded config, at which point this class will be quite big
    (compare cmk/base/default_config/base ...)
    """

    # TODO: get `HostAddress` VS. `str` right! Which is it at what point?!
    # NOTE: all of the below is wishful typing, no parsing is done yet.
    # for now we just copy what we find in default_config
    folder_attributes: Mapping[str, FolderAttributesForBase]
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]]
    checkgroup_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    static_checks: Mapping[
        str, list[RuleSpec[list[object]]]
    ]  # a.k.a. "enforced_services". Keep the name for consistency
    service_rule_groups: set[str]
    service_descriptions: Mapping[str, str]
    service_description_translation: Sequence[RuleSpec[Mapping[str, object]]]
    use_new_descriptions_for: Container[str]
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
    timeperiods: object  # Here we don't lie for a change. We haven't parsed anything.
    check_periods: Sequence[RuleSpec[object]]
    relays: object  # see above
    cmc_config_multiprocessing: object
