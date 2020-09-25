#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import (
    Any,
    List,
    Dict,
    Mapping,
    Generator,
)
from cmk.utils.regex import regex
from .agent_based_api.v1 import (
    Service,
    Result,
    register,
    State as state,
)

from .agent_based_api.v1.type_defs import (
    AgentStringTable,
    CheckResult,
    DiscoveryResult,
    Parameters,
)
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


def parse_windows_services(string_table: AgentStringTable) -> Dict[str, Dict[str, str]]:
    def to_service(status: str, description: str) -> Dict[str, str]:
        cur_state, start_type = status.split('/', 1) if "/" in status else (status, "unknown")
        return {
            "state": cur_state,
            "start_type": start_type,
            "description": description,
        }

    return {
        name: to_service(status, " ".join(description))
        for name, status, *description in string_table
    }


register.agent_section(
    name="services",
    parse_function=parse_windows_services,
)


def discovery_windows_services(params: List[Dict[str, Any]],
                               section: Dict[str, Dict[str, str]]) -> DiscoveryResult:

    # Handle single entries (type str)
    def add_matching_services(name, description, service_state, start_type, entry):
        # New wato rule handling
        svc, *statespec = entry
        # First match name or description (optional since rule based config option available)
        if svc:
            if svc.startswith("~"):
                r = regex(svc[1:])

                if not r.match(name) and not r.match(description):
                    return
            elif svc not in (name, description):
                return

        if isinstance(statespec, list):
            # New wato rule handling (always given as tuple of two)
            if (statespec[0] and statespec[0] != service_state) or (statespec[1] and
                                                                    statespec[1] != start_type):
                return

        else:
            for match_criteria in statespec.split("/"):
                if match_criteria not in {service_state, start_type}:
                    return
        yield Service(item=name)

    # Extract the WATO compatible rules for the current host
    rules = []

    # In case no rule is set by user, *no* windows services should be discovered.
    # Therefore always skip the default settings which are the last element of the list.
    for value in params[:-1]:
        # Now extract the list of service regexes
        svcs = value.get('services', [])
        service_state = value.get('state', None)
        start_mode = value.get('start_mode', None)
        if svcs:
            for svc in svcs:
                rules.append(('~' + svc, service_state, start_mode))
        else:
            rules.append((None, service_state, start_mode))

    for service_name, service_details in section.items():
        for rule in rules:
            yield from add_matching_services(service_name, service_details["description"],
                                             service_details["state"],
                                             service_details["start_type"], rule)


# Format of parameters
# {
#    "states" : [ ( "running", "demand", 1 ),
#                  ( "stopped", None, 2 ) ],
#    "else" : 2,
# }
def check_windows_services(item: str, params: Parameters,
                           section: Dict[str, Dict[str, str]]) -> Generator[Result, None, None]:

    # allow to match agains the internal name or agains the display name
    # of the service
    for service_name, service_details in section.items():
        service_state = service_details["state"]
        service_description = service_details["description"]
        service_start_type = service_details["start_type"]
        if item in (service_name, service_description) or service_name in params.get(
                "additional_servicenames", []):

            for t_state, t_start_type, mon_state in params.get("states", [("running", None, 0)]):
                if (t_state is None or t_state == service_state) \
                 and (t_start_type is None or t_start_type == service_start_type):
                    this_state = mon_state
                    break
                this_state = params.get("else", 2)

            yield Result(
                state=state(this_state),
                summary="%s: %s (start type is %s)" %
                (service_description, service_state, service_start_type),
            )


def cluster_check_windows_services(item: str, params: Parameters,
                                   section: Mapping[str, Dict[str, Dict[str, str]]]) -> CheckResult:
    # A service may appear more than once (due to clusters).
    # First make a list of all matching entries with their
    # states
    found = []
    for node, services in section.items():
        results = list(check_windows_services(item, params, services))
        if results:
            found.append((node, results[0]))

    if not found:
        yield Result(state=state(params.get("else", 2)), summary="service not found")
        return

    # We take the best found state (neccessary for clusters)
    best_state = state.best(*(result.state for _node, result in found))
    best_running_on, best_result = [(n, r) for n, r in found if r.state == best_state][-1]

    yield best_result
    if best_running_on and best_state != state.CRIT:
        yield Result(state=best_state, summary="Running on: %s" % best_running_on)


register.check_plugin(
    name="services",
    service_name="Service %s",
    discovery_ruleset_type="all",
    discovery_ruleset_name="inventory_services_rules",
    discovery_function=discovery_windows_services,
    discovery_default_parameters=WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS,
    check_ruleset_name="services",
    check_default_parameters=WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS,
    check_function=check_windows_services,
    cluster_check_function=cluster_check_windows_services,
)


def discovery_services_summary(section: Dict[str, Dict[str, str]]) -> DiscoveryResult:
    if section:
        yield Service()


def check_services_summary(params: Parameters, section: Dict[str, Dict[str, str]]) -> CheckResult:
    blacklist = params.get("ignored", [])
    stoplist = []
    num_blacklist = 0
    num_auto = 0

    for service_name, service_details in section.items():

        if service_details["start_type"] == "auto":
            num_auto += 1
            if service_details["state"] == "stopped":
                match = False
                for srv in blacklist:
                    if re.match(srv, service_name):
                        match = True
                if match is False:
                    stoplist.append(service_name)
                else:
                    num_blacklist += 1
    num_stoplist = len(stoplist)
    num_srv = len(section.keys())

    if num_stoplist > 0:
        stopped_srvs = " (" + ", ".join(stoplist) + ")"
        cur_state = state(params.get("state_if_stopped", 0))
    else:
        stopped_srvs = ""
        cur_state = state.OK

    yield Result(
        state=cur_state,
        summary=
        "%d services, %d services in autostart - of which %d services are stopped%s, %d services stopped but ignored"
        % (num_srv, num_auto, num_stoplist, stopped_srvs, num_blacklist),
    )


register.check_plugin(
    name="services_summary",
    sections=["services"],
    service_name="Service Summary",
    discovery_function=discovery_services_summary,
    check_function=check_services_summary,
    check_default_parameters=SERVICES_SUMMARY_DEFAULT_PARAMETERS,
    check_ruleset_name="services_summary",
)
