#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Any, Dict, Generator, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from .agent_based_api.v1 import regex, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

# Output of old agent (< 1.1.10i2):
# AeLookupSvc        running  Application Experience Lookup Service
# Alerter            stopped  Alerter
# ALG                stopped  Application Layer Gateway Service
# AppMgmt            stopped  Application Management
# appmgr             running  Remote Server Manager

# Output of new agent (>= 1.1.10i2):
# Alerter stopped/disabled Warndienst
# ALG running/demand Gatewaydienst auf Anwendungsebene
# Apple_Mobile_Device running/auto Apple Mobile Device
# AppMgmt stopped/demand Anwendungsverwaltung
# AudioSrv running/auto Windows Audio
# BITS running/demand Intelligenter Hintergrund<FC>bertragungsdienst
# Bonjour_Service running/auto Dienst "Bonjour"

# Implemented in 1.2.1i2:
# New rule-style (WATO compatible) notation:
#   [({'start_mode': 'demand', 'service': ['Netman']}, [], ['@all'], {'docu_url': ''})]
#
# <services> is list of regexes matching the service name
# <state> is the expected state to inventorize services of (running, stopped, ...)
# <start_mode> is the expected state to inventorize services of (auto, manual, ...)

WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS: Dict[str, Any] = {}

WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS = {
    "states": [("running", None, 0)],
    "else": 2,
    "additional_servicenames": [],
}

SERVICES_SUMMARY_DEFAULT_PARAMETERS = {"ignored": [], "state_if_stopped": 0}


class WinService(NamedTuple):
    name: str
    state: str
    start_type: str
    description: str


Section = List[WinService]  # deterministic order!


def parse_windows_services(string_table: StringTable) -> Section:
    def to_service(name: str, status: str, description: str) -> WinService:
        cur_state, start_type = status.split("/", 1) if "/" in status else (status, "unknown")
        return WinService(name, cur_state, start_type, description)

    return [
        to_service(name, status, " ".join(description))
        for name, status, *description in string_table
    ]


register.agent_section(
    name="services",
    parse_function=parse_windows_services,
)


def _extract_wato_compatible_rules(
    params: Sequence[Mapping[str, Any]],
) -> Sequence[Tuple[Optional[str], Optional[str], Optional[str]]]:
    return [
        (pattern, rule.get("state"), rule.get("start_mode"))
        # If no rule is set by user, *no* windows services should be discovered.
        # Skip the default settings which are the last element of the list:
        for rule in params[:-1]
        for pattern in rule.get("services") or [None]
    ]


def _add_matching_services(
    service: WinService,
    pattern: Optional[str],
    state: Optional[str],
    mode: Optional[str],
) -> DiscoveryResult:
    if pattern:
        # First match name or description (optional since rule based config option available)
        expr = regex(pattern)
        if not (expr.match(service.name) or expr.match(service.description)):
            return

    if (state and state != service.state) or (mode and mode != service.start_type):
        return

    yield Service(item=service.name)


def discovery_windows_services(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    # Extract the WATO compatible rules for the current host
    rules = _extract_wato_compatible_rules(params)

    for service in section:
        for rule in rules:
            yield from _add_matching_services(service, *rule)


def check_windows_services_single(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> Generator[Result, None, None]:
    """
    >>> for result in check_windows_services_single(
    ...    item="GoodService",
    ...    params={'additional_servicenames': [], 'else': 0, 'states': [('running', 'auto', 0)]},
    ...    section=[WinService(name='GoodService', state='stopped', start_type='demand', description='nixda')]):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='nixda: stopped (start type is demand)')
    """
    # allow to match agains the internal name or agains the display name of the service
    additional_names = params.get("additional_servicenames", [])
    for service in section:
        if _matches_item(service, item) or service.name in additional_names:
            yield Result(
                state=_match_service_against_params(params, service),
                summary=f"{service.description}: {service.state} (start type is {service.start_type})",
            )


def _matches_item(service: WinService, item: str) -> bool:
    return item in (service.name, service.description)


def _match_service_against_params(params: Mapping[str, Any], service: WinService) -> State:
    """
    This function searches params for the first rule that matches the state and the start_type.
    None is treated as a wildcard. If no match is found, the function defaults.
    """
    for t_state, t_start_type, mon_state in params.get("states", [("running", None, 0)]):
        if _wildcard(t_state, service.state) and _wildcard(t_start_type, service.start_type):
            return State(mon_state)
    return State(params.get("else", 2))


def _wildcard(value, reference):
    return value is None or value == reference


def check_windows_services(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> Generator[Result, None, None]:
    results = list(check_windows_services_single(item, params, section))
    if results:
        yield from results
    else:
        yield Result(state=State(params.get("else", 2)), summary="service not found")


def cluster_check_windows_services(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[Section]],
) -> CheckResult:
    # A service may appear more than once (due to clusters).
    # First make a list of all matching entries with their
    # states
    found = []
    for node, node_section in section.items():
        if node_section is None:
            continue
        results = list(check_windows_services_single(item, params, node_section))
        if results:
            found.append((node, results[0]))

    if not found:
        yield Result(state=State(params.get("else", 2)), summary="service not found")
        return

    # We take the best found state (neccessary for clusters)
    best_state = State.best(*(result.state for _node, result in found))
    best_running_on, best_result = [(n, r) for n, r in found if r.state == best_state][-1]

    yield best_result
    if best_running_on and best_state != State.CRIT:
        yield Result(state=best_state, summary="Running on: %s" % best_running_on)


register.check_plugin(
    name="services",
    service_name="Service %s",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_ruleset_name="inventory_services_rules",
    discovery_function=discovery_windows_services,
    discovery_default_parameters=WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS,
    check_ruleset_name="services",
    check_default_parameters=WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS,
    check_function=check_windows_services,
    cluster_check_function=cluster_check_windows_services,
)


def discovery_services_summary(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_services_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    blacklist = params.get("ignored", [])
    stoplist = []
    num_blacklist = 0
    num_auto = 0

    for service in section:
        if service.start_type != "auto":
            continue

        num_auto += 1
        if service.state == "stopped":
            if any(re.match(srv, service.name) for srv in blacklist):
                num_blacklist += 1
            else:
                stoplist.append(service.name)

    yield Result(
        state=State.OK,
        summary=f"Autostart services: {num_auto}",
        details=f"Autostart services: {num_auto}\nServices found in total: {len(section)}",
    )

    yield Result(
        state=State(params.get("state_if_stopped", 0)) if stoplist else State.OK,
        summary=f"Stopped services: {len(stoplist)}",
        details=("Stopped services: %s" % ", ".join(stoplist)) if stoplist else None,
    )

    if num_blacklist:
        yield Result(state=State.OK, notice=f"Stopped but ignored: {num_blacklist}")


register.check_plugin(
    name="services_summary",
    sections=["services"],
    service_name="Service Summary",
    discovery_function=discovery_services_summary,
    check_function=check_services_summary,
    check_default_parameters=SERVICES_SUMMARY_DEFAULT_PARAMETERS,
    check_ruleset_name="services_summary",
)
