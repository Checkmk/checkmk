#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Defining builting rule spec groups"""

from cmk.gui.i18n import _

from .rulespecs import rulespec_group_registry, RulespecGroup, RulespecSubGroup


@rulespec_group_registry.register
class RulespecGroupMonitoringConfiguration(RulespecGroup):
    @property
    def name(self):
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


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationVarious(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "various"

    @property
    def title(self) -> str:
        return _("Various")


@rulespec_group_registry.register
class RulespecGroupHostsMonitoringRules(RulespecGroup):
    @property
    def name(self):
        return "host_monconf"

    @property
    def title(self) -> str:
        return _("Host monitoring rules")

    @property
    def help(self):
        return _("Rules to configure the behaviour of monitored hosts.")


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationServiceChecks(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "service_checks"

    @property
    def title(self) -> str:
        return _("Service Checks")


@rulespec_group_registry.register
class RulespecGroupHostsMonitoringRulesVarious(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self):
        return "host_various"

    @property
    def title(self) -> str:
        return _("Various")


@rulespec_group_registry.register
class RulespecGroupMonitoringConfigurationNotifications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self):
        return "notifications"

    @property
    def title(self) -> str:
        return _("Notifications")


@rulespec_group_registry.register
class RulespecGroupHostsMonitoringRulesNotifications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self):
        return "host_notifications"

    @property
    def title(self) -> str:
        return _("Notifications")


@rulespec_group_registry.register
class RulespecGroupHostsMonitoringRulesHostChecks(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupHostsMonitoringRules

    @property
    def sub_group_name(self):
        return "host_checks"

    @property
    def title(self) -> str:
        return _("Host checks")


@rulespec_group_registry.register
class RulespecGroupAgentSNMP(RulespecGroup):
    @property
    def name(self):
        return "snmp"

    @property
    def title(self) -> str:
        return _("SNMP rules")

    @property
    def help(self):
        return _("Configure SNMP related settings using rulesets")


@rulespec_group_registry.register
class RulespecGroupMonitoringAgents(RulespecGroup):
    @property
    def name(self):
        return "agents"

    @property
    def title(self) -> str:
        return _("Agent rules")

    @property
    def help(self):
        return _("Configuration of monitoring agents for Linux, Windows and Unix")


@rulespec_group_registry.register
class RulespecGroupMonitoringAgentsGenericOptions(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupMonitoringAgents

    @property
    def sub_group_name(self):
        return "generic_options"

    @property
    def title(self) -> str:
        return _("Generic Options")


@rulespec_group_registry.register
class RulespecGroupEnforcedServices(RulespecGroup):
    @property
    def name(self):
        return "static"

    @property
    def title(self) -> str:
        return _("Enforced services")

    @property
    def help(self):
        return _(
            "Rules to set up [wato_services#manual_checks|manual services]. Services set "
            "up in this way do not depend on the service discovery. This is useful if you want "
            "to enforce compliance with a specific guideline. You can for example ensure that "
            "a certain Windows service is always present on a host."
        )


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesNetworking(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "networking"

    @property
    def title(self) -> str:
        return _("Networking")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesApplications(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "applications"

    @property
    def title(self) -> str:
        return _("Applications, Processes & Services")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesEnvironment(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "environment"

    @property
    def title(self) -> str:
        return _("Temperature, Humidity, Electrical Parameters, etc.")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self) -> str:
        return _("Operating System Resources")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "hardware"

    @property
    def title(self) -> str:
        return _("Hardware, BIOS")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesStorage(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "storage"

    @property
    def title(self) -> str:
        return _("Storage, Filesystems and Files")


@rulespec_group_registry.register
class RulespecGroupEnforcedServicesVirtualization(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupEnforcedServices

    @property
    def sub_group_name(self):
        return "virtualization"

    @property
    def title(self) -> str:
        return _("Virtualization")
