#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Dict, Mapping, MutableMapping, Optional

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Metric,
    register,
    render,
    Result,
    Service,
)
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.livestatus_status import LivestatusSection

# Example output from agent:
# <<<livestatus_status:sep(59)>>>
# [downsite]
# [mysite]
# accept_passive_host_checks;accept_passive_service_checks;cached_log_messages;check_external_commands;check_host_freshness;check_service_freshness;connections;connections_rate;enable_event_handlers;enable_flap_detection;enable_notifications;execute_host_checks;execute_service_checks;external_command_buffer_max;external_command_buffer_slots;external_command_buffer_usage;external_commands;external_commands_rate;forks;forks_rate;host_checks;host_checks_rate;interval_length;last_command_check;last_log_rotation;livecheck_overflows;livecheck_overflows_rate;livechecks;livechecks_rate;livestatus_active_connections;livestatus_queued_connections;livestatus_threads;livestatus_version;log_messages;log_messages_rate;nagios_pid;neb_callbacks;neb_callbacks_rate;num_hosts;num_services;obsess_over_hosts;obsess_over_services;process_performance_data;program_start;program_version;requests;requests_rate;service_checks;service_checks_rate
# 1;1;0;1;0;1;231;1.0327125668e-01;1;1;1;1;1;0;32768;0;0;0.0000000000e+00;0;0.0000000000e+00;0;0.0000000000e+00;60;1359471450;0;0;0.0000000000e+00;0;0.0000000000e+00;1;0;20;2013.01.23;0;0.0000000000e+00;15126;15263;6.5307324420e+00;0;0;0;0;1;1359469039;3.2.3;230;1.0327125668e-01;0;0.0000000000e+00

livestatus_status_default_levels = {
    "site_stopped": 2,
    "execute_host_checks": 2,
    "execute_service_checks": 2,
    "accept_passive_host_checks": 2,
    "accept_passive_service_checks": 2,
    "check_host_freshness": 0,  # Was in OMD the default up to now, better not warn
    "check_service_freshness": 1,
    "enable_event_handlers": 1,
    "enable_flap_detection": 1,
    "enable_notifications": 2,
    "process_performance_data": 1,
    "check_external_commands": 2,
    "site_cert_days": (30, 7),
    "average_latency_generic": (30, 60),
    "average_latency_cmk": (30, 60),
    "average_latency_fetcher": (30, 60),
    "helper_usage_generic": (80.0, 90.0),
    "helper_usage_cmk": (80.0, 90.0),
    "helper_usage_fetcher": (80.0, 90.0),
    "helper_usage_checker": (80.0, 90.0),
    "livestatus_usage": (60.0, 80.0),
    "livestatus_overflows_rate": (0.01, 0.02),
}


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


register.agent_section(
    name="livestatus_status",
    parse_function=parse_livestatus_status,
)


def parse_livestatus_ssl_certs(string_table: StringTable) -> LivestatusSection:
    parsed: Dict[str, Dict[str, str]] = {}
    site = None
    for line in string_table:
        if line and line[0][0] == "[" and line[0][-1] == "]":
            site = line[0][1:-1]
            parsed[site] = {}

        elif site and len(line) == 2:
            pem_path, valid_until = line
            parsed[site][pem_path] = valid_until

    return parsed


register.agent_section(
    name="livestatus_ssl_certs",
    parse_function=parse_livestatus_ssl_certs,
)


def discovery_livestatus_status(
    section_livestatus_status: Optional[LivestatusSection],
    section_livestatus_ssl_certs: Optional[LivestatusSection],
) -> DiscoveryResult:
    if section_livestatus_status is None:
        return
    for site, status in section_livestatus_status.items():
        if status is not None:
            yield Service(item=site)


def check_livestatus_status(
    item: str,
    params: Mapping[str, Any],
    section_livestatus_status: Optional[LivestatusSection],
    section_livestatus_ssl_certs: Optional[LivestatusSection],
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


def _generate_livestatus_results(
    item: str,
    params: Mapping[str, Any],
    section_livestatus_status: Optional[LivestatusSection],
    section_livestatus_ssl_certs: Optional[LivestatusSection],
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
    if section_livestatus_status is None or item not in section_livestatus_status:
        return
    status = section_livestatus_status[item]

    # Ignore down sites. This happens on a regular basis due to restarts
    # of the core. The availability of a site is monitored with 'omd_status'.
    if status is None:
        yield Result(state=state(params["site_stopped"]), summary="Site is currently not running")
        return

    yield Result(state=state.OK, summary="Livestatus version: %s" % status["livestatus_version"])

    for key, title in [
        ("host_checks", "Host checks"),
        ("service_checks", "Service checks"),
        ("forks", "Process creations"),
        ("connections", "Livestatus connects"),
        ("requests", "Livestatus requests"),
        ("log_messages", "Log messages"),
    ]:
        try:
            value = get_rate(
                value_store=value_store,
                key=key,
                time=this_time,
                value=float(status[key]),
            )
        except GetRateError as error:
            yield IgnoreResults(str(error))
            continue

        if key in ("host_checks", "service_checks"):
            yield Result(state=state.OK, summary="%s: %.1f/s" % (title, value))
        else:
            yield Result(state=state.OK, notice="%s: %.1f/s" % (title, value))

        yield Metric(name=key, value=value, boundaries=(0, None))

    if status["program_version"].startswith("Check_MK"):
        # We have a CMC here.

        for factor, render_func, key, label in [
            (1, lambda x: "%.3fs" % x, "average_latency_generic", "Average check latency"),
            (1, lambda x: "%.3fs" % x, "average_latency_cmk", "Average Checkmk latency"),
            (1, lambda x: "%.3fs" % x, "average_latency_fetcher", "Average fetcher latency"),
            (100, render.percent, "helper_usage_generic", "Check helper usage"),
            (100, render.percent, "helper_usage_cmk", "Checkmk helper usage"),
            (100, render.percent, "helper_usage_fetcher", "Fetcher helper usage"),
            (100, render.percent, "helper_usage_checker", "Checker helper usage"),
            (100, render.percent, "livestatus_usage", "Livestatus usage"),
            (1, lambda x: "%.1f/s" % x, "livestatus_overflows_rate", "Livestatus overflow rate"),
        ]:

            try:
                value = factor * float(status[key])
            except KeyError:
                # may happen if we are trying to query old host
                if key in [
                    "helper_usage_fetcher",
                    "helper_usage_checker",
                    "average_latency_fetcher",
                ]:
                    value = 0.0
                else:
                    raise

            yield from check_levels(
                value=value,
                metric_name=key,
                levels_upper=params[key],
                render_func=render_func,
                label=label,
                notice_only=True,
                boundaries=(0, None),
            )

    yield from check_levels(
        value=int(status["num_hosts"]),
        metric_name="monitored_hosts",
        levels_upper=params.get("levels_hosts"),
        label="Hosts",
        notice_only=True,
        boundaries=(0, None),
    )
    yield from check_levels(
        value=int(status["num_services"]),
        metric_name="monitored_services",
        levels_upper=params.get("levels_services"),
        label="Services",
        notice_only=True,
        boundaries=(0, None),
    )
    # Output some general information
    yield Result(
        state=state.OK,
        notice="Core version: %s" % status["program_version"].replace("Check_MK", "Checkmk"),
    )

    # cert_valid_until should only be empty in one case that we know of so far:
    # the value is collected via the linux special agent with the command 'date'
    # for 32bit systems, dates after 19th Jan 2038 (32bit limit)
    # the 'date'-command will return an error and thus no result
    # this happens e.g. for hacky raspberry pi setups that are not officially supported
    pem_path = "/omd/sites/%s/etc/ssl/sites/%s.pem" % (item, item)
    valid_until_str = (
        None
        if section_livestatus_ssl_certs is None
        else section_livestatus_ssl_certs.get(item, {}).get(pem_path)
    )
    if valid_until_str:
        valid_until = int(valid_until_str)
        yield Result(
            state=state.OK,
            notice="Site certificate valid until %s" % render.date(valid_until),
        )
        secs_left = valid_until - this_time
        warn_d, crit_d = params["site_cert_days"]
        yield from check_levels(
            value=secs_left,
            label="Expiring in",
            levels_lower=None if None in (warn_d, crit_d) else (warn_d * 86400.0, crit_d * 86400.0),
            render_func=render.timespan,
            notice_only=True,
            boundaries=(0, None),
        )
        yield Metric("site_cert_days", secs_left / 86400.0)

    settings = [
        ("execute_host_checks", "Active host checks are disabled"),
        ("execute_service_checks", "Active service checks are disabled"),
        ("accept_passive_host_checks", "Passive host check are disabled"),
        ("accept_passive_service_checks", "Passive service checks are disabled"),
        ("check_host_freshness", "Host freshness checking is disabled"),
        ("check_service_freshness", "Service freshness checking is disabled"),
        #   ("enable_event_handlers",         "Alert handlers are disabled"), # special case below
        ("enable_flap_detection", "Flap detection is disabled"),
        ("enable_notifications", "Notifications are disabled"),
        ("process_performance_data", "Performance data is disabled"),
        ("check_external_commands", "External commands are disabled"),
    ]
    # Check settings of enablings. Here we are quiet unless a non-OK state is found
    for settingname, title in settings:
        if status[settingname] != "1":
            yield Result(state=state(params[settingname]), notice=title)

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
            state=state(params["enable_event_handlers"]),
            notice="Alert handlers are disabled",
        )


register.check_plugin(
    name="livestatus_status",
    sections=["livestatus_status", "livestatus_ssl_certs"],
    service_name="OMD %s performance",
    check_ruleset_name="livestatus_status",
    discovery_function=discovery_livestatus_status,
    check_function=check_livestatus_status,
    check_default_parameters=livestatus_status_default_levels,
)
