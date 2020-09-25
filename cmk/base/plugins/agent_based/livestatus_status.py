#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import (
    Dict,
    Any,
)
from .agent_based_api.v1 import (
    register,
    Service,
    Result,
    Metric,
    State as state,
    get_rate,
    get_value_store,
    render,
    check_levels,
)
from .agent_based_api.v1.type_defs import (
    AgentStringTable,
    CheckResult,
    DiscoveryResult,
    Parameters,
)

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
    "helper_usage_generic": (60.0, 90.0),
    "helper_usage_cmk": (60.0, 90.0),
    "helper_usage_fetcher": (40.0, 80.0),
    "helper_usage_checker": (40.0, 80.0),
    "livestatus_usage": (80.0, 90.0),
    "livestatus_overflows_rate": (0.01, 0.02),
}

ParsedSection = Dict[str, Any]


def parse_livestatus_status(string_table: AgentStringTable):
    parsed: ParsedSection = {}
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


def parse_livestatus_ssl_certs(string_table: AgentStringTable):
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


def discovery_livestatus_status(section_livestatus_status: ParsedSection,
                                section_livestatus_ssl_certs: ParsedSection) -> DiscoveryResult:

    for site, status in section_livestatus_status.items():
        if status is not None:
            yield Service(item=site)


def check_livestatus_status(item: str, params: Parameters, section_livestatus_status: ParsedSection,
                            section_livestatus_ssl_certs: ParsedSection) -> CheckResult:
    if item not in section_livestatus_status:
        return
    status = section_livestatus_status[item]

    # Ignore down sites. This happens on a regular basis due to restarts
    # of the core. The availability of a site is monitored with 'omd_status'.
    if status is None:
        yield Result(state=state(params["site_stopped"]), summary="Site is currently not running")
        return

    # Check Performance counters
    this_time = time.time()
    for key, title in [
        ("host_checks", "HostChecks"),
        ("service_checks", "ServiceChecks"),
        ("forks", "ProcessCreations"),
        ("connections", "LivestatusConnects"),
        ("requests", "LivestatusRequests"),
        ("log_messages", "LogMessages"),
    ]:
        value = get_rate(
            value_store=get_value_store(),
            key="livestatus_status.%s.%s" % (item, key),
            time=this_time,
            value=float(status[key]),
        )
        yield Result(state=state.OK, summary="%s: %.1f/s" % (title, value))
        yield Metric(name=key, value=value)

    if status["program_version"].startswith("Check_MK"):
        # We have a CMC here.

        for factor, human_func, key, title in [
            (1, lambda x: "%.3fs" % x, "average_latency_generic", "Average check latency"),
            (1, lambda x: "%.3fs" % x, "average_latency_cmk", "Average Checkmk latency"),
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
                if key in ["helper_usage_fetcher", "helper_usage_checker"]:
                    value = 0.0
                else:
                    raise

            yield from check_levels(value=value,
                                    metric_name=key,
                                    levels_upper=params.get(key),
                                    render_func=human_func,
                                    label=title)

    yield from check_levels(
        value=int(status["num_hosts"]),
        metric_name="monitored_hosts",
        levels_upper=params.get("levels_hosts"),
        label="Monitored Hosts",
    )
    yield from check_levels(
        value=int(status["num_services"]),
        metric_name="monitored_services",
        levels_upper=params.get("levels_services"),
        label="Services",
    )
    # Output some general information
    yield Result(state=state.OK,
                 summary="Core version: %s" %
                 status["program_version"].replace("Check_MK", "Checkmk"))
    yield Result(state=state.OK, summary="Livestatus version: %s" % status["livestatus_version"])

    # cert_valid_until should only be empty in one case that we know of so far:
    # the value is collected via the linux special agent with the command 'date'
    # for 32bit systems, dates after 19th Jan 2038 (32bit limit)
    # the 'date'-command will return an error and thus no result
    # this happens e.g. for hacky raspberry pi setups that are not officially supported
    pem_path = "/omd/sites/%s/etc/ssl/sites/%s.pem" % (item, item)
    cert_valid_until = section_livestatus_ssl_certs.get(item, {}).get(pem_path)
    if cert_valid_until is not None and cert_valid_until != '':
        days_left = (int(cert_valid_until) - time.time()) / 86400.0
        valid_until_formatted = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(int(cert_valid_until)))

        yield from check_levels(
            value=days_left,
            metric_name="site_cert_days",
            label="Site certificate validity (until %s)" % valid_until_formatted,
            levels_lower=(params["site_cert_days"][0], params["site_cert_days"][1]),
        )

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
        if status[settingname] != '1' and params[settingname] != 0:
            yield Result(state=state(params[settingname]), summary=title)

    # special considerations for enable_event_handlers
    if status["program_version"].startswith("Check_MK 1.2.6"):
        # In CMC <= 1.2.6 event handlers cannot be enabled. So never warn.
        return
    if status.get("has_event_handlers", '1') == '0':
        # After update from < 1.2.7 the check would warn about disabled alert
        # handlers since they are disabled in this case. But the user has no alert
        # handlers defined, so this is nothing to warn about. Start warn when the
        # user defines his first alert handlers.
        return
    if status["enable_event_handlers"] != '1' and params["enable_event_handlers"] != 0:
        yield Result(state=state(params["enable_event_handlers"]),
                     summary="Alert handlers are disabled")


register.check_plugin(
    name="livestatus_status",
    sections=["livestatus_status", "livestatus_ssl_certs"],
    service_name="OMD %s performance",
    check_ruleset_name="livestatus_status",
    discovery_function=discovery_livestatus_status,
    check_function=check_livestatus_status,
    check_default_parameters=livestatus_status_default_levels,
)
