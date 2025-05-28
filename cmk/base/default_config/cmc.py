#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Defaults settings for global configuration

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from cmk.ccc.hostaddress import HostName

from cmk.utils.rulesets.ruleset_matcher import RuleSpec

cmc_check_helpers = 5
cmc_fetcher_helpers = 13
cmc_checker_helpers = 4
cmc_real_time_helpers = 1


class CMCConfigMultiprocessingMandatory(TypedDict):
    use_multiprocessing: bool


class CMCConfigMultiprocessing(CMCConfigMultiprocessingMandatory, total=False):
    limit_workers: int


cmc_config_multiprocessing: CMCConfigMultiprocessing = {"use_multiprocessing": True}
cmc_pnp_update_delay = 3600
cmc_pnp_update_on_restart = False
cmc_state_retention_interval = 600  # sec
cmc_log_rotation_method = 3  # weekly
cmc_log_limit = 50 * 1024 * 1024  # for rotation at this size
cmc_check_timeout = 60  # sec
# ruleset to override cmc_check_timeout for services
cmc_service_check_timeout: Sequence[RuleSpec[int]] = []
cmc_flap_settings = (3.0, 5.0, 0.1)  # low/high threshold, decay per minute
# Service ruleset
cmc_service_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = []
# Host ruleset
cmc_host_flap_settings: Sequence[RuleSpec[tuple[float, float, float]]] = []


class CMCInitialScheduling(TypedDict):
    burst: int
    spread_cmk: int
    spread_generic: int


cmc_initial_scheduling: CMCInitialScheduling = {
    "burst": 10,
    "spread_cmk": 1200,
    "spread_generic": 150,
}
cmc_housekeeping_interval = 1000  # ms
cmc_smartping_check_interval = 500  # ms
# This is a ruleset for hosts
cmc_smartping_settings: Sequence[RuleSpec[Mapping[str, float]]] = []


class SmartPingTuningBase(TypedDict):
    omit_payload: bool
    num_sockets: int
    ignore_rst: bool


class RealTimeChecks(TypedDict):
    port: int
    secret: str


class SmartPingTuning(SmartPingTuningBase, total=False):
    throttling: tuple


cmc_smartping_tuning: SmartPingTuning = {
    "omit_payload": False,
    "num_sockets": 8,
    "ignore_rst": False,
}

cmc_dump_core = False
cmc_log_levels: dict[str, int] = {
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


class LogCmkHelpers(TypedDict):
    log_level: int
    debug: bool


cmc_log_cmk_helpers: LogCmkHelpers = {"log_level": 0, "debug": False}
cmc_log_microtime = False
cmc_livestatus_threads = 20
cmc_max_response_size = 100  # MB
cmc_livestatus_logcache_size = 500000
cmc_livestatus_lines_per_file = 1000000  # maximum allows lines per logfile


class _CMCStatehistCacheMandatory(TypedDict):
    horizon: int  # seconds
    max_core_downtime: int  # seconds


class CMCStatehistCache(_CMCStatehistCacheMandatory, total=False):
    tarpit: int


cmc_statehist_cache: CMCStatehistCache = {"horizon": 63072000, "max_core_downtime": 30}
cmc_debug_notifications = False
max_long_output_size: int = 2000


class CMCAuthorization(TypedDict):
    host: Literal[0, 1]
    group: Literal[0, 1]


cmc_authorization: CMCAuthorization = {"host": 0, "group": 0}
cmc_timeperiod_horizon = 2 * 365
cmc_import_nagios_state = True


class CMCGraphiteConnection(TypedDict):
    host: HostName
    port: int
    prefix: str
    mangling: bool


# was previously None or a single dict
cmc_graphite: list[CMCGraphiteConnection] = []

# ruleset for services
cmc_graphite_host_metrics: Sequence[RuleSpec[Sequence[str]]] = []
cmc_graphite_service_metrics: Sequence[RuleSpec[Sequence[str]]] = []
cmc_influxdb_service_metrics: Sequence[RuleSpec[Mapping[str, Any]]] = []
influxdb_connections: dict[str, dict[str, Any]] = {}
cmc_host_limit: int | None = None  # Do not allow more than this number of hosts
cmc_service_limit: int | None = None  # Do not allow more than this number of services
shadow_hosts: dict[HostName, dict[str, Any]] = {}
cmc_store_params_in_config = False
cmc_service_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = []
cmc_host_long_output_in_monitoring_history: Sequence[RuleSpec[bool]] = []
service_state_translation: Sequence[RuleSpec[Mapping[object, object]]] = []
host_state_translation: Sequence[RuleSpec[Mapping[object, object]]] = []

# Features of CEE that do not (only) belong to the core
cmc_real_time_checks: RealTimeChecks | None = None

host_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = []
service_recurring_downtimes: Sequence[RuleSpec[Mapping[str, int | str]]] = []

# BEGIN Deprecated options. Kept for compatibility with existing config files
cmc_smartping_omit_payload = False
cmc_log_level = 5  # Replaced by cmc_log_levels
cmc_livestatus_debug = 0  # Replaced by cmc_log_levels
cmc_debug_alerts = False  # Replaced by cmc_log_levels
# END Deprecated options. Kept for compatibility with existing config files
