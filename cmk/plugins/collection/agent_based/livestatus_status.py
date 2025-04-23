#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import MutableMapping
from typing import Any, Literal, NotRequired, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.livestatus_status import LivestatusSection

# Example output from agent:
# <<<livestatus_status:sep(59)>>>
# [downsite]
# [mysite]
# accept_passive_host_checks;accept_passive_service_checks;cached_log_messages;check_external_commands;check_host_freshness;check_service_freshness;connections;connections_rate;enable_event_handlers;enable_flap_detection;enable_notifications;execute_host_checks;execute_service_checks;external_command_buffer_max;external_command_buffer_slots;external_command_buffer_usage;external_commands;external_commands_rate;forks;forks_rate;host_checks;host_checks_rate;interval_length;last_command_check;last_log_rotation;livecheck_overflows;livecheck_overflows_rate;livechecks;livechecks_rate;livestatus_active_connections;livestatus_queued_connections;livestatus_threads;livestatus_version;log_messages;log_messages_rate;nagios_pid;neb_callbacks;neb_callbacks_rate;num_hosts;num_services;obsess_over_hosts;obsess_over_services;process_performance_data;program_start;program_version;requests;requests_rate;service_checks;service_checks_rate
# 1;1;0;1;0;1;231;1.0327125668e-01;1;1;1;1;1;0;32768;0;0;0.0000000000e+00;0;0.0000000000e+00;0;0.0000000000e+00;60;1359471450;0;0;0.0000000000e+00;0;0.0000000000e+00;1;0;20;2013.01.23;0;0.0000000000e+00;15126;15263;6.5307324420e+00;0;0;0;0;1;1359469039;3.2.3;230;1.0327125668e-01;0;0.0000000000e+00


type _StateInt = Literal[0, 1, 2, 3]


class LivestatusStatusParameters(TypedDict):
    site_stopped: _StateInt
    execute_host_checks: _StateInt
    execute_service_checks: _StateInt
    accept_passive_host_checks: _StateInt
    accept_passive_service_checks: _StateInt
    check_host_freshness: _StateInt
    check_service_freshness: _StateInt
    enable_event_handlers: _StateInt
    enable_flap_detection: _StateInt
    enable_notifications: _StateInt
    process_performance_data: _StateInt
    check_external_commands: _StateInt
    site_cert_days: tuple[int, int]  # >= 0
    average_latency_generic: tuple[int, int]
    average_latency_cmk: tuple[int, int]
    average_latency_fetcher: tuple[int, int]
    helper_usage_generic: tuple[float, float]
    helper_usage_fetcher: tuple[float, float]
    helper_usage_checker: tuple[float, float]
    livestatus_usage: tuple[float, float]
    livestatus_overflows_rate: tuple[float, float]
    levels_hosts: NotRequired[tuple[int, int]]
    levels_services: NotRequired[tuple[int, int]]
    carbon_overflows_rate: NotRequired[tuple[float, float]]
    carbon_queue_usage: NotRequired[tuple[float, float]]
    influxdb_overflows_rate: NotRequired[tuple[float, float]]
    influxdb_queue_usage: NotRequired[tuple[float, float]]
    rrdcached_overflows_rate: NotRequired[tuple[float, float]]
    rrdcached_queue_usage: NotRequired[tuple[float, float]]


livestatus_status_default_levels = LivestatusStatusParameters(
    site_stopped=2,
    execute_host_checks=2,
    execute_service_checks=2,
    accept_passive_host_checks=2,
    accept_passive_service_checks=2,
    check_host_freshness=0,  # Was in OMD the default up to now, better not warn
    check_service_freshness=1,
    enable_event_handlers=1,
    enable_flap_detection=1,
    enable_notifications=2,
    process_performance_data=1,
    check_external_commands=2,
    site_cert_days=(30, 7),
    average_latency_generic=(30, 60),
    average_latency_cmk=(30, 60),
    average_latency_fetcher=(30, 60),
    helper_usage_generic=(80.0, 90.0),
    helper_usage_fetcher=(80.0, 90.0),
    helper_usage_checker=(80.0, 90.0),
    livestatus_usage=(60.0, 80.0),
    livestatus_overflows_rate=(0.01, 0.02),
)


_PEM_PATH_TEMPLATE = "/omd/sites/{site}/etc/ssl/sites/{site}.pem"


def parse_livestatus_status(string_table: StringTable) -> LivestatusSection:
    parsed: LivestatusSection = {}
    site, headers = None, None
    for line in string_table:
        if line and line[0][0] == "[" and line[0][-1] == "]":
            site = line[0][1:-1]
            parsed[site] = None  # Site is marked as down until overwritten later

        elif site:
            if headers is None:
                headers = line
            else:
                parsed[site] = dict(zip(headers, line))
                headers = None

    return parsed


agent_section_livestatus_status = AgentSection(
    name="livestatus_status",
    parse_function=parse_livestatus_status,
)


def parse_livestatus_ssl_certs(string_table: StringTable) -> LivestatusSection:
    parsed: dict[str, dict[str, str]] = {}
    site = None
    for line in string_table:
        if line and line[0][0] == "[" and line[0][-1] == "]":
            site = line[0][1:-1]
            parsed[site] = {}

        elif site and len(line) == 2:
            pem_path, valid_until = line
            parsed[site][pem_path] = valid_until

    return parsed


agent_section_livestatus_ssl_certs = AgentSection(
    name="livestatus_ssl_certs",
    parse_function=parse_livestatus_ssl_certs,
)


def discovery_livestatus_status(
    section_livestatus_status: LivestatusSection | None,
    section_livestatus_ssl_certs: LivestatusSection | None,
) -> DiscoveryResult:
    if section_livestatus_status is None:
        return
    for site, status in section_livestatus_status.items():
        if status is not None:
            yield Service(item=site)


def check_livestatus_status(
    item: str,
    params: LivestatusStatusParameters,
    section_livestatus_status: LivestatusSection | None,
    section_livestatus_ssl_certs: LivestatusSection | None,
) -> CheckResult:
    # Check Performance counters
    this_time = time.time()
    value_store = get_value_store()
    yield from _generate_livestatus_results(
        item,
        params,
        section_livestatus_status,
        section_livestatus_ssl_certs,
        value_store,
        this_time,
    )


def _make_levels(raw_days: tuple[float | None, float | None]) -> None | tuple[float, float]:
    match raw_days:
        case float(w), float(c):
            return (w * 86400.0, c * 86400.0)
    return None


def _check_livestatus_cert(
    section_livestatus_ssl_certs: LivestatusSection,
    item: str,
    this_time: float,
    params: LivestatusStatusParameters,
) -> CheckResult:
    # cert_valid_until should only be empty in one case that we know of so far:
    # the value is collected via the linux special agent with the command 'date'
    # for 32bit systems, dates after 19th Jan 2038 (32bit limit)
    # the 'date'-command will return an error and thus no result
    # this happens e.g. for hacky raspberry pi setups that are not officially supported
    if not (
        valid_until_str := section_livestatus_ssl_certs.get(item, {}).get(
            _PEM_PATH_TEMPLATE.format(site=item)
        )
    ):
        return

    valid_until = int(valid_until_str)
    secs_left = valid_until - this_time
    yield Result(
        state=State.OK,
        notice=f"Site certificate valid until {render.date(valid_until)}",
    )
    yield Metric("site_cert_days", secs_left / 86400.0)
    if secs_left < 0:
        yield Result(
            state=State.CRIT,  # at the time of writing this, levels are always configured >=0
            summary=f"Expired {render.timespan(-secs_left)} ago",
        )
    else:
        yield from check_levels_v1(
            value=secs_left,
            label="Expiring in",
            levels_lower=_make_levels(params["site_cert_days"]),
            render_func=render.timespan,
            notice_only=True,
        )


def _generate_livestatus_results(
    item: str,
    params: LivestatusStatusParameters,
    section_livestatus_status: LivestatusSection | None,
    section_livestatus_ssl_certs: LivestatusSection | None,
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
    if section_livestatus_status is None or item not in section_livestatus_status:
        return
    status = section_livestatus_status[item]

    # Ignore down sites. This happens on a regular basis due to restarts
    # of the core. The availability of a site is monitored with 'omd_status'.
    if status is None:
        yield Result(state=State(params["site_stopped"]), summary="Site is currently not running")
        return

    yield Result(state=State.OK, summary="Livestatus version: %s" % status["livestatus_version"])

    for metric_name, key, title in [
        ("host_checks", "host_checks_rate", "Host checks"),
        ("service_checks", "service_checks_rate", "Service checks"),
        ("forks", "forks_rate", "Process creations"),
        ("connections", "connections_rate", "Livestatus connects"),
        ("requests", "requests_rate", "Livestatus requests"),
        ("log_messages", "log_messages_rate", "Log messages"),
    ]:
        value = float(status[key])
        if key in ("host_checks_rate", "service_checks_rate"):
            yield Result(state=State.OK, summary=f"{title}: {value:.1f}/s")
        else:
            yield Result(state=State.OK, notice=f"{title}: {value:.1f}/s")

        yield Metric(name=metric_name, value=value, boundaries=(0, None))

    if status["program_version"].startswith("Check_MK"):
        # We have a CMC here.
        metrics = [
            (1, lambda x: "%.3fs" % x, "average_latency_generic", "Average active check latency"),
            (1, lambda x: "%.3fs" % x, "average_latency_checker", "Average checker latency"),
            (1, lambda x: "%.3fs" % x, "average_latency_fetcher", "Average fetcher latency"),
            (100, render.percent, "helper_usage_generic", "Active check helper usage"),
            (100, render.percent, "helper_usage_fetcher", "Fetcher helper usage"),
            (100, render.percent, "helper_usage_checker", "Checker helper usage"),
            (100, render.percent, "livestatus_usage", "Livestatus usage"),
            (1, lambda x: "%.2f/s" % x, "livestatus_overflows_rate", "Livestatus overflow rate"),
            (1, lambda x: "%d/s" % x, "perf_data_count_rate", "Rate of performance data received"),
            (1, lambda x: "%d/s" % x, "metrics_count_rate", "Rate of metrics received"),
        ]
        for conn, name in (("carbon", "Carbon"), ("influxdb", "InfluxDB"), ("rrdcached", "RRD")):
            metrics.extend(
                (
                    (100, render.percent, f"{conn}_queue_usage", f"{name} queue usage"),
                    (
                        100,
                        lambda x: "%d/s" % x,
                        f"{conn}_queue_usage_rate",
                        f"{name} queue usage rate",
                    ),
                    (
                        1,
                        lambda x: "%d/s" % x,
                        f"{conn}_overflows_rate",
                        f"Rate of performance data loss for {name}",
                    ),
                    (
                        1,
                        render.iobandwidth,
                        f"{conn}_bytes_sent_rate",
                        f"Rate of bytes sent to the {name} connection",
                    ),
                )
            )
        for factor, render_func, key, label in metrics:
            try:
                value = factor * float(status[key])
            except KeyError:
                # may happen if we are trying to query old host
                if key == "average_latency_checker":
                    value = float(status["average_latency_cmk"])
                elif key in [
                    "helper_usage_fetcher",
                    "helper_usage_checker",
                    "average_latency_fetcher",
                    "carbon_overflows_rate",
                    "carbon_queue_usage",
                    "carbon_queue_usage_rate",
                    "carbon_bytes_sent_rate",
                    "influxdb_overflows_rate",
                    "influxdb_queue_usage",
                    "influxdb_queue_usage_rate",
                    "influxdb_bytes_sent_rate",
                    "rrdcached_overflows_rate",
                    "rrdcached_queue_usage",
                    "rrdcached_queue_usage_rate",
                    "rrdcached_bytes_sent_rate",
                    "perf_data_count_rate",
                    "metrics_count_rate",
                ]:
                    value = 0.0
                else:
                    raise

            # The column was incorrectly named, but we want to keep the parameter configuration and the persisted metrics.
            if key == "average_latency_checker":
                key = "average_latency_cmk"

            yield from check_levels_v1(
                value=value,
                metric_name=key,
                # Suppression: the key is not always one of the literals :-(
                levels_upper=params.get(key),  # type: ignore[call-overload]
                render_func=render_func,
                label=label,
                notice_only=True,
                boundaries=(0, None),
            )

    yield from check_levels_v1(
        value=int(status["num_hosts"]),
        metric_name="monitored_hosts",
        levels_upper=params.get("levels_hosts"),
        label="Hosts",
        notice_only=True,
        boundaries=(0, None),
    )
    yield from check_levels_v1(
        value=int(status["num_services"]),
        metric_name="monitored_services",
        levels_upper=params.get("levels_services"),
        label="Services",
        notice_only=True,
        boundaries=(0, None),
    )
    # Output some general information
    yield Result(
        state=State.OK,
        notice="Core version: %s" % status["program_version"].replace("Check_MK", "Checkmk"),
    )

    if section_livestatus_ssl_certs is not None:
        yield from _check_livestatus_cert(section_livestatus_ssl_certs, item, this_time, params)

    setting_messages = {
        "execute_host_checks": "Active host checks are disabled",
        "execute_service_checks": "Active service checks are disabled",
        "accept_passive_host_checks": "Passive host check are disabled",
        "accept_passive_service_checks": "Passive service checks are disabled",
        "check_host_freshness": "Host freshness checking is disabled",
        "check_service_freshness": "Service freshness checking is disabled",
        #   "enable_event_handlers":         "Alert handlers are disabled", # special case below
        "enable_flap_detection": "Flap detection is disabled",
        "enable_notifications": "Notifications are disabled",
        "process_performance_data": "Performance data is disabled",
        "check_external_commands": "External commands are disabled",
    }
    # Check settings of enablings. Here we are quiet unless a non-OK state is found
    for p_name, p_value in params.items():
        if p_name in setting_messages and status[p_name] != "1":
            yield Result(state=State(p_value), notice=setting_messages[p_name])

    # special considerations for enable_event_handlers
    if status["program_version"].startswith("Check_MK 1.2.6"):
        # In CMC <= 1.2.6 event handlers cannot be enabled. So never warn.
        return
    if status.get("has_event_handlers", "1") == "0":
        # After update from < 1.2.7 the check would warn about disabled alert
        # handlers since they are disabled in this case. But the user has no alert
        # handlers defined, so this is nothing to warn about. Start warn when the
        # user defines his first alert handlers.
        return
    if status["enable_event_handlers"] != "1":
        yield Result(
            state=State(params["enable_event_handlers"]),
            notice="Alert handlers are disabled",
        )


check_plugin_livestatus_status = CheckPlugin(
    name="livestatus_status",
    sections=["livestatus_status", "livestatus_ssl_certs"],
    service_name="OMD %s performance",
    check_ruleset_name="livestatus_status",
    discovery_function=discovery_livestatus_status,
    check_function=check_livestatus_status,
    check_default_parameters=livestatus_status_default_levels,
)
