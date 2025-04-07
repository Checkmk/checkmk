#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Defining built-in rule spec groups"""

from cmk.gui.i18n import _

from .rulespecs import (
    RulespecGroup,
    RulespecGroupEnforcedServices,
    RulespecGroupRegistry,
    RulespecSubGroup,
)


def register(rulespec_group_registry: RulespecGroupRegistry) -> None:
    rulespec_group_registry.register(RulespecGroupMonitoringConfiguration)
    rulespec_group_registry.register(RulespecGroupMonitoringConfigurationVarious)
    rulespec_group_registry.register(RulespecGroupHostsMonitoringRules)
    rulespec_group_registry.register(RulespecGroupMonitoringConfigurationServiceChecks)
    rulespec_group_registry.register(RulespecGroupHostsMonitoringRulesVarious)
    rulespec_group_registry.register(RulespecGroupMonitoringConfigurationNotifications)
    rulespec_group_registry.register(RulespecGroupHostsMonitoringRulesNotifications)
    rulespec_group_registry.register(RulespecGroupHostsMonitoringRulesHostChecks)
    rulespec_group_registry.register(RulespecGroupAgentSNMP)
    rulespec_group_registry.register(RulespecGroupMonitoringAgents)
    rulespec_group_registry.register(RulespecGroupMonitoringAgentsGenericOptions)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesNetworking)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesApplications)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesEnvironment)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesOperatingSystem)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesHardware)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesStorage)
    rulespec_group_registry.register(RulespecGroupEnforcedServicesVirtualization)


class RulespecGroupMonitoringConfiguration(RulespecGroup):
    @property
    def name(self) -> str:
        return "monconf"

    @property
    def title(self) -> str:
        return _("Service monitoring rules")

    @property
    def help(self):
        return _(
            "Rules to configure existing services in the monitoring. For "
            "example, threshold values can be set, the execution time for "
            "active checks can be configured or attributes such as labels "
            "or tags can be assigned to the services."
        )


class RulespecGroupMonitoringConfigurationVarious(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "various"

    @property
    def title(self) -> str:
        return _("Various")


class RulespecGroupHostsMonitoringRules(RulespecGroup):
    @property
    def name(self) -> str:
        return "host_monconf"

    @property
    def title(self) -> str:
        return _("Host monitoring rules")

    @property
    def help(self):
        return _("Rules to configure the behavior of monitored hosts.")


class RulespecGroupMonitoringConfigurationServiceChecks(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "service_checks"

    @property
    def title(self) -> str:
        return _("Service Checks")


class RulespecGroupHostsMonitoringRulesVarious(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self) -> str:
        return "host_various"

    @property
    def title(self) -> str:
        return _("Various")


class RulespecGroupMonitoringConfigurationNotifications(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "notifications"

    @property
    def title(self) -> str:
        return _("Notifications")


class RulespecGroupHostsMonitoringRulesNotifications(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self) -> str:
        return "host_notifications"

    @property
    def title(self) -> str:
        return _("Notifications")


class RulespecGroupHostsMonitoringRulesHostChecks(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self) -> str:
        return "host_checks"

    @property
    def title(self) -> str:
        return _("Host checks")


class RulespecGroupAgentSNMP(RulespecGroup):
    @property
    def name(self) -> str:
        return "snmp"

    @property
    def title(self) -> str:
        return _("SNMP rules")

    @property
    def help(self):
        return _("Configure SNMP related settings using rule sets")


class RulespecGroupMonitoringAgents(RulespecGroup):
    @property
    def name(self) -> str:
        return "agents"

    @property
    def title(self) -> str:
        return _("Agent rules")

    @property
    def help(self):
        return _("Configuration of monitoring agents for Linux, Windows and Unix")


class RulespecGroupMonitoringAgentsGenericOptions(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    def sub_group_name(self) -> str:
        return "generic_options"

    @property
    def title(self) -> str:
        return _("Generic agent options")


class RulespecGroupEnforcedServicesNetworking(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "networking"

    @property
    def title(self) -> str:
        return _("Networking")


class RulespecGroupEnforcedServicesApplications(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "applications"

    @property
    def title(self) -> str:
        return _("Applications, Processes & Services")


class RulespecGroupEnforcedServicesEnvironment(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "environment"

    @property
    def title(self) -> str:
        return _("Temperature, Humidity, Electrical Parameters, etc.")


class RulespecGroupEnforcedServicesOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "os"

    @property
    def title(self) -> str:
        return _("Operating System Resources")


class RulespecGroupEnforcedServicesHardware(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "hardware"

    @property
    def title(self) -> str:
        return _("Hardware, BIOS")


class RulespecGroupEnforcedServicesStorage(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "storage"

    @property
    def title(self) -> str:
        return _("Storage, file systems and files")


class RulespecGroupEnforcedServicesVirtualization(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self) -> str:
        return "virtualization"

    @property
    def title(self) -> str:
        return _("Virtualization")
