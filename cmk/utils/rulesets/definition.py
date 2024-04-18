#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum


class RuleGroupType(enum.Enum):
    ACTIVE_CHECKS = "active_checks"
    AGENT_CONFIG = "agent_config"
    EXTRA_HOST_CONF = "extra_host_conf"
    EXTRA_SERVICE_CONF = "extra_service_conf"
    INV_EXPORTS = "inv_exports"
    INV_PARAMETERS = "inv_parameters"
    NOTIFICATION_PARAMETERS = "notification_parameters"
    SPECIAL_AGENTS = "special_agents"
    STATIC_CHECKS = "static_checks"
    CHECKGROUP_PARAMETERS = "checkgroup_parameters"


class RuleGroup:
    @staticmethod
    def ActiveChecks(name: str | None) -> str:
        return f"{RuleGroupType.ACTIVE_CHECKS.value}:{name}"

    @staticmethod
    def is_active_checks_rule(rule_name: str) -> bool:
        return rule_name.startswith(f"{RuleGroupType.ACTIVE_CHECKS.value}:")

    @staticmethod
    def AgentConfig(name: str | None) -> str:
        return f"{RuleGroupType.AGENT_CONFIG.value}:{name}"

    @staticmethod
    def ExtraHostConf(name: str | None) -> str:
        return f"{RuleGroupType.EXTRA_HOST_CONF.value}:{name}"

    @staticmethod
    def ExtraServiceConf(name: str | None) -> str:
        return f"{RuleGroupType.EXTRA_SERVICE_CONF.value}:{name}"

    @staticmethod
    def InvExports(name: str | None) -> str:
        return f"{RuleGroupType.INV_EXPORTS.value}:{name}"

    @staticmethod
    def InvParameters(name: str | None) -> str:
        return f"{RuleGroupType.INV_PARAMETERS.value}:{name}"

    @staticmethod
    def NotificationParameters(name: str | None) -> str:
        return f"{RuleGroupType.NOTIFICATION_PARAMETERS.value}:{name}"

    @staticmethod
    def SpecialAgents(name: str | None) -> str:
        return f"{RuleGroupType.SPECIAL_AGENTS.value}:{name}"

    @staticmethod
    def is_special_agents_rule(rule_name: str) -> bool:
        return rule_name.startswith(f"{RuleGroupType.SPECIAL_AGENTS.value}:")

    @staticmethod
    def StaticChecks(name: str | None) -> str:
        return f"{RuleGroupType.STATIC_CHECKS.value}:{name}"

    @staticmethod
    def CheckgroupParameters(name: str | None) -> str:
        return f"{RuleGroupType.CHECKGROUP_PARAMETERS.value}:{name}"


def is_from_ruleset_group(rule_name: str, group_type: RuleGroupType) -> bool:
    return rule_name.startswith(f"{group_type.value}:")
