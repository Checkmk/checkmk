#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Alertmanager Check"""

import json
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Tuple, TypedDict

from .agent_based_api.v1 import register, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


class RuleState(Enum):
    INACTIVE = "inactive"
    FIRING = "firing"
    PENDING = "pending"
    NONE = "none"
    NA = None


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    NONE = "none"
    NA = None

    @classmethod
    def _missing_(cls, value):
        return Severity.NA


class Rule(NamedTuple):
    rule_name: str
    group_name: str
    status: RuleState
    severity: Severity
    message: Optional[str]


Group = Dict[str, Rule]
Section = Dict[str, Group]

StateMapping = Dict[str, int]


class GroupServices(TypedDict, total=False):
    min_amount_rules: int
    no_group_services: List[str]


class DiscoveryParams(TypedDict, total=False):
    # TODO: Remove total=False and mark summary_service as
    # not required when upgrading to Python 3.10:
    # https://www.python.org/dev/peps/pep-0655/
    group_services: Tuple[bool, GroupServices]
    summary_service: bool


class AlertRemapping(TypedDict):
    rule_names: List[str]
    map: StateMapping


class CheckParams(TypedDict, total=False):
    alert_remapping: List[AlertRemapping]


default_discovery_parameters = DiscoveryParams(
    group_services=(
        True,
        GroupServices(
            min_amount_rules=3,
            no_group_services=[],
        ),
    ),
    summary_service=True,
)

default_check_parameters = CheckParams(
    alert_remapping=[
        AlertRemapping(
            rule_names=["Watchdog"],
            map={"inactive": 2, "pending": 2, "firing": 0, "none": 2, "n/a": 2},
        )
    ]
)

default_state_mapping = {
    RuleState.INACTIVE: state.OK,
    RuleState.PENDING: state.OK,
    RuleState.FIRING: state.CRIT,
    RuleState.NONE: state.UNKNOWN,
    RuleState.NA: state.UNKNOWN,
}


def _get_summary_count(section: Section) -> int:
    return sum(len(group) for group in section.values())


def _get_mapping(rule: Rule, params: CheckParams) -> Optional[StateMapping]:
    """Returns remapping for a specific rule if one exists"""
    for mapping in params.get("alert_remapping", []):
        if rule.rule_name in mapping["rule_names"]:
            return mapping["map"]
    return None


def _create_group_service(group_name: str, group: Group, params: DiscoveryParams) -> bool:
    use_groups, group_config = params["group_services"]
    if not use_groups:
        return False
    return (
        group_name not in group_config["no_group_services"]
        and len(group) >= group_config["min_amount_rules"]
    )


def _get_rule_state(rule: Rule, params: CheckParams) -> state:
    mapping = _get_mapping(rule, params)
    if mapping:
        # Needed because Dicts cannot handle "None" as Key but Enums can
        return state(mapping[rule.status.value if rule.status.value else "n/a"])
    return default_state_mapping[rule.status]


def parse_alertmanager(string_table: type_defs.StringTable) -> Section:
    section: Section = {}
    alertmanager_section = json.loads(string_table[0][0])
    for group, rules in alertmanager_section.items():
        for rule in rules:
            section.setdefault(group, {}).setdefault(
                rule["name"],
                Rule(
                    rule["name"],
                    group,
                    RuleState(rule["state"]),
                    Severity(rule["severity"]),
                    rule["message"],
                ),
            )
    return section


register.agent_section(
    name="alertmanager",
    parse_function=parse_alertmanager,
)

#   .--Rules---------------------------------------------------------------.
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___  ___                      |
#   |                        | |_) | | | | |/ _ \/ __|                     |
#   |                        |  _ <| |_| | |  __/\__ \                     |
#   |                        |_| \_\\__,_|_|\___||___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_alertmanager_rules(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for group_name, rules in section.items():
        if _create_group_service(group_name, rules, params):
            continue

        for rule in rules.values():
            yield Service(item=rule.rule_name)


def check_alertmanager_rules(item: str, params: CheckParams, section: Section) -> CheckResult:
    for group in section.values():
        rule = group.get(item)
        if rule:
            status = _get_rule_state(rule, params)
            if rule.severity:
                yield Result(
                    state=state.OK,
                    summary="Severity: %s" % rule.severity.value,
                )
            yield Result(
                state=state.OK,
                summary="Group name: %s" % rule.group_name,
            )
            if status != state.OK:
                yield Result(
                    state=status,
                    summary="Active alert",
                    details=rule.message if rule.message else "No message",
                )


register.check_plugin(
    name="alertmanager_rules",
    sections=["alertmanager"],
    service_name="Alert Rule %s",
    check_function=check_alertmanager_rules,
    check_ruleset_name="alertmanager_rule_state",
    check_default_parameters=default_check_parameters,
    discovery_function=discovery_alertmanager_rules,
    discovery_ruleset_name="discovery_alertmanager",
    discovery_default_parameters=default_discovery_parameters,
)

#   .--Groups--------------------------------------------------------------.
#   |                      ____                                            |
#   |                     / ___|_ __ ___  _   _ _ __  ___                  |
#   |                    | |  _| '__/ _ \| | | | '_ \/ __|                 |
#   |                    | |_| | | | (_) | |_| | |_) \__ \                 |
#   |                     \____|_|  \___/ \__,_| .__/|___/                 |
#   |                                        |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_alertmanager_groups(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for group_name, rules in section.items():
        if _create_group_service(group_name, rules, params):
            yield Service(item=group_name)


def check_alertmanager_groups(item: str, params: CheckParams, section: Section) -> CheckResult:
    group = section.get(item)
    if group:
        yield Result(state=state.OK, summary="Number of rules: %s" % len(group))
        for rule in group.values():
            status = _get_rule_state(rule, params)
            if status != state.OK:
                yield Result(
                    state=status,
                    summary="Active alert: %s" % rule.rule_name,
                    details="%s: %s"
                    % (rule.rule_name, rule.message if rule.message else "No message"),
                )


register.check_plugin(
    name="alertmanager_groups",
    sections=["alertmanager"],
    service_name="Alert Rule Group %s",
    check_function=check_alertmanager_groups,
    check_ruleset_name="alertmanager_rule_state",
    check_default_parameters=default_check_parameters,
    discovery_function=discovery_alertmanager_groups,
    discovery_ruleset_name="discovery_alertmanager",
    discovery_default_parameters=default_discovery_parameters,
)

#   .--Summary-------------------------------------------------------------.
#   |            ____                                                      |
#   |           / ___| _   _ _ __ ___  _ __ ___   __ _ _ __ _   _          |
#   |           \___ \| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |         |
#   |            ___) | |_| | | | | | | | | | | | (_| | |  | |_| |         |
#   |           |____/ \__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |         |
#   |                                                       |___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_alertmanager_summary(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    if params.get("summary_service"):
        yield Service()


def check_alertmanager_summary(params: CheckParams, section: Section) -> CheckResult:
    yield Result(state=state.OK, summary="Number of rules: %s" % _get_summary_count(section))
    for rules in section.values():
        for rule in rules.values():
            status = _get_rule_state(rule, params)
            if status != state.OK:
                yield Result(
                    state=status,
                    summary="Active alert: %s" % rule.rule_name,
                    details="%s: %s"
                    % (rule.rule_name, rule.message if rule.message else "No message"),
                )


register.check_plugin(
    name="alertmanager_summary",
    sections=["alertmanager"],
    service_name="Alertmanager Summary",
    check_function=check_alertmanager_summary,
    check_ruleset_name="alertmanager_rule_state_summary",
    check_default_parameters=default_check_parameters,
    discovery_function=discovery_alertmanager_summary,
    discovery_ruleset_name="discovery_alertmanager",
    discovery_default_parameters=default_discovery_parameters,
)
