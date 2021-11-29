#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import IntEnum
from typing import Dict, TypedDict

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class IisAppPoolState(IntEnum):
    Uninitialized = 1
    Initialized = 2
    Running = 3
    Disabling = 4
    Disabled = 5
    ShutdownPending = 6
    DeletePending = 7


Section = Dict[str, IisAppPoolState]


class IisAppPoolStateCheckParams(TypedDict):
    state_mapping: Dict[str, int]


DefaultCheckParameters: IisAppPoolStateCheckParams = dict(
    state_mapping={
        app_state.name: {IisAppPoolState.Running: State.OK, IisAppPoolState.Initialized: State.WARN}
        .get(app_state, State.CRIT)
        .value
        for app_state in IisAppPoolState
    }
)


def parse_iis_app_pool_state(string_table: StringTable) -> Section:
    """
    >>> parse_iis_app_pool_state([["app name ", " 3"]])
    {'app name': <IisAppPoolState.Running: 3>}
    """
    return {app.strip(): IisAppPoolState(int(state)) for app, state in string_table}


register.agent_section(
    name="iis_app_pool_state",
    parse_function=parse_iis_app_pool_state,
)


def discover_iis_app_pool_state(section: Section) -> DiscoveryResult:
    """
    >>> list(discover_iis_app_pool_state({
    ...     'app0': IisAppPoolState.Running,
    ...     'app1': IisAppPoolState.Running,
    ... }))
    [Service(item='app0'), Service(item='app1')]
    """
    for app in section.keys():
        yield Service(item=app)


def check_iis_app_pool_state(
    item: str, params: IisAppPoolStateCheckParams, section: Section
) -> CheckResult:
    """
    >>> list(check_iis_app_pool_state("app0", DefaultCheckParameters, {"app0": IisAppPoolState.Running}))
    [Result(state=<State.OK: 0>, summary='State: Running')]
    """
    app_state = section.get(item)
    if app_state is None:
        yield Result(state=State.UNKNOWN, summary=f"{item} is unknown")
        return

    state_value = params.get("state_mapping", {}).get(app_state.name, State.CRIT.value)
    yield Result(state=State(state_value), summary=f"State: {section[item].name}")


register.check_plugin(
    name="iis_app_pool_state",
    service_name="IIS Application Pool '%s'",
    discovery_function=discover_iis_app_pool_state,
    check_function=check_iis_app_pool_state,
    check_default_parameters=DefaultCheckParameters,
    check_ruleset_name="iis_app_pool_state",
)
