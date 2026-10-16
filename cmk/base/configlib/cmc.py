#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The configuration of the Checkmk Micro Core (CMC)"""

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.matcher import RuleSpec


class CMCInitialScheduling(TypedDict):
    burst: int
    spread_cmk: int
    spread_generic: int


class SmartPingTuningBase(TypedDict):
    omit_payload: bool
    num_sockets: int
    ignore_rst: bool


class SmartPingTuning(SmartPingTuningBase, total=False):
    throttling: tuple  # type: ignore[type-arg]


class RealTimeChecks(TypedDict):
    port: int
    secret: str


class LogCmkHelpers(TypedDict):
    log_level: int
    debug: bool


class CMCAuthorization(TypedDict):
    host: Literal[0, 1]
    group: Literal[0, 1]


class CMCGraphiteConnection(TypedDict):
    host: HostName
    port: int
    prefix: str
    mangling: bool


@dataclasses.dataclass(frozen=True, kw_only=True)
class CMCConfigFields:
    cmc_check_helpers: int = 5
    cmc_fetcher_helpers: int = 13
    cmc_checker_helpers: int = 4
    cmc_real_time_helpers: int = 1
    cmc_config_multiprocessing: object = dataclasses.field(
        default_factory=lambda: {"use_multiprocessing": True}
    )
    cmc_pnp_update_delay: int = 3600
    cmc_pnp_update_on_restart: bool = False
    cmc_state_retention_interval: int = 600
    cmc_log_rotation_method: int = 3
    cmc_log_limit: int = 50 * 1024 * 1024
    cmc_check_timeout: int = 60
    cmc_service_check_timeout: Sequence[RuleSpec[int]] = dataclasses.field(default_factory=list)
    cmc_flap_settings: tuple[float, float, float] = (3.0, 5.0, 0.1)
    cmc_service_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_host_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_initial_scheduling: CMCInitialScheduling = dataclasses.field(
        default_factory=lambda: CMCInitialScheduling(burst=10, spread_cmk=1200, spread_generic=150)
    )
    cmc_housekeeping_interval: int = 1000
    cmc_smartping_check_interval: int = 500
    cmc_smartping_settings: Sequence[RuleSpec[Mapping[str, float]]] = dataclasses.field(
        default_factory=list
    )
    cmc_smartping_tuning: SmartPingTuning = dataclasses.field(
        default_factory=lambda: SmartPingTuning(omit_payload=False, num_sockets=8, ignore_rst=False)
    )
    cmc_dump_core: bool = False
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
    cmc_log_cmk_helpers: LogCmkHelpers = dataclasses.field(
        default_factory=lambda: LogCmkHelpers(log_level=0, debug=False)
    )
    cmc_log_microtime: bool = False
    cmc_livestatus_threads: int = 20
    cmc_max_response_size: int = 100
    cmc_livestatus_logcache_size: int = 500000
    cmc_livestatus_lines_per_file: int = 1000000
    cmc_statehist_cache: Mapping[str, object] | None = dataclasses.field(
        default_factory=lambda: {"horizon": 63072000, "max_core_downtime": 30}
    )
    cmc_debug_notifications: bool = False
    max_long_output_size: int = 2000
    cmc_authorization: CMCAuthorization = dataclasses.field(
        default_factory=lambda: CMCAuthorization(host=0, group=0)
    )
    cmc_timeperiod_horizon: int = 2 * 365
    cmc_import_nagios_state: bool = True
    cmc_graphite: Sequence[CMCGraphiteConnection] = dataclasses.field(default_factory=list)
    cmc_graphite_host_metrics: Sequence[RuleSpec[Sequence[str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_graphite_service_metrics: Sequence[RuleSpec[Sequence[str]]] = dataclasses.field(
        default_factory=list
    )
    cmc_influxdb_service_metrics: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    influxdb_connections: Mapping[str, dict[str, object]] = dataclasses.field(default_factory=dict)
    cmc_host_limit: int | None = None
    cmc_service_limit: int | None = None
    shadow_hosts: dict[HostName, dict[str, object]] = dataclasses.field(default_factory=dict)
    cmc_store_params_in_config: bool = False
    cmc_service_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = dataclasses.field(
        default_factory=list
    )
    cmc_host_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = dataclasses.field(
        default_factory=list
    )
    service_state_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    host_state_translation: Sequence[RuleSpec[Mapping[str, object]]] = dataclasses.field(
        default_factory=list
    )
    cmc_real_time_checks: RealTimeChecks | None = None
    host_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = dataclasses.field(
        default_factory=list
    )
    service_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = dataclasses.field(
        default_factory=list
    )
