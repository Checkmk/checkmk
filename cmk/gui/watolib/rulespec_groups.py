#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Defining built-in rule spec groups"""

from cmk.gui.i18n import _
from cmk.gui.utils.urls import DocReference

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
    rulespec_group_registry.register(RulespecGroupAgent)
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

    rulespec_group_registry.register(RulespecGroupDiscoveryCheckParameters)
    rulespec_group_registry.register(RulespecGroupCheckParametersNetworking)
    rulespec_group_registry.register(RulespecGroupCheckParametersStorage)
    rulespec_group_registry.register(RulespecGroupCheckParametersOperatingSystem)
    rulespec_group_registry.register(RulespecGroupCheckParametersPrinters)
    rulespec_group_registry.register(RulespecGroupCheckParametersEnvironment)
    rulespec_group_registry.register(RulespecGroupCheckParametersApplications)
    rulespec_group_registry.register(RulespecGroupCheckParametersVirtualization)
    rulespec_group_registry.register(RulespecGroupCheckParametersHardware)
    rulespec_group_registry.register(RulespecGroupCheckParametersDiscovery)

    rulespec_group_registry.register(RulespecGroupVMCloudContainer)
    rulespec_group_registry.register(RulespecGroupDatasourcePrograms)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsOS)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsApps)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsCloud)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsCustom)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsContainer)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsHardware)
    rulespec_group_registry.register(RulespecGroupDatasourceProgramsTesting)

    rulespec_group_registry.register(RulespecGroupIntegrateOtherServices)
    rulespec_group_registry.register(RulespecGroupActiveChecks)


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


class RulespecGroupAgent(RulespecGroup):
    @property
    def name(self) -> str:
        return "agent"

    @property
    def title(self) -> str:
        return _("Access to agents")

    @property
    def help(self):
        return _("Settings concerning the connection to the Checkmk and SNMP agents")


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


class RulespecGroupDiscoveryCheckParameters(RulespecGroup):
    @property
    def name(self) -> str:
        return "checkparams"

    @property
    def title(self) -> str:
        return _("Service discovery rules")

    @property
    def help(self):
        return _(
            "Rules that influence the discovery of services. These rules "
            "allow, for example, the execution of a periodic service "
            "discovery or the deactivation of check plug-ins and services. "
            "Additionally, the discovery of individual check plug-ins like "
            "for example the interface check plug-in can "
            "be customized."
        )


class RulespecGroupCheckParametersNetworking(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "networking"

    @property
    def title(self) -> str:
        return _("Networking")


class RulespecGroupCheckParametersStorage(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "storage"

    @property
    def title(self) -> str:
        return _("Storage, file systems and files")


class RulespecGroupCheckParametersOperatingSystem(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "os"

    @property
    def title(self) -> str:
        return _("Operating System Resources")


class RulespecGroupCheckParametersPrinters(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "printers"

    @property
    def title(self) -> str:
        return _("Printers")


class RulespecGroupCheckParametersEnvironment(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "environment"

    @property
    def title(self) -> str:
        return _("Temperature, Humidity, Electrical Parameters, etc.")


class RulespecGroupCheckParametersApplications(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "applications"

    @property
    def title(self) -> str:
        return _("Applications, Processes & Services")


class RulespecGroupCheckParametersVirtualization(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "virtualization"

    @property
    def title(self) -> str:
        return _("Virtualization")


class RulespecGroupCheckParametersHardware(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringConfiguration

    @property
    def sub_group_name(self) -> str:
        return "hardware"

    @property
    def title(self) -> str:
        return _("Hardware, BIOS")


class RulespecGroupCheckParametersDiscovery(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDiscoveryCheckParameters

    @property
    def sub_group_name(self) -> str:
        return "discovery"

    @property
    def title(self) -> str:
        return _("Discovery of individual services")


class RulespecGroupVMCloudContainer(RulespecGroup):
    @property
    def name(self) -> str:
        return "vm_cloud_container"

    @property
    def title(self) -> str:
        return _("VM, cloud, container")

    @property
    def help(self):
        return _("Integrate with VM, cloud or container platforms")

    @property
    def doc_references(self) -> dict[DocReference, str]:
        return {
            DocReference.WATO_AGENTS: _("Monitoring agents"),
            DocReference.VMWARE: _("Monitoring VMWare ESXi"),
            DocReference.AWS: _("Monitoring Amazon Web Services (AWS)"),
            DocReference.AZURE: _("Monitoring Microsoft Azure"),
            DocReference.GCP: _("Monitoring Google Cloud Platform (GCP)"),
            DocReference.KUBERNETES: _("Monitoring Kubernetes"),
            DocReference.PROMETHEUS: _("Integrating Prometheus"),
        }


class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self) -> str:
        return "datasource_programs"

    @property
    def title(self) -> str:
        return _("Other integrations")

    @property
    def help(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")


class RulespecGroupDatasourceProgramsOS(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "os"

    @property
    def title(self) -> str:
        return _("Operating systems")


class RulespecGroupDatasourceProgramsApps(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "apps"

    @property
    def title(self) -> str:
        return _("Applications")


class RulespecGroupDatasourceProgramsCloud(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "cloud"

    @property
    def title(self) -> str:
        return _("Cloud based environments")


class RulespecGroupDatasourceProgramsContainer(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "container"

    @property
    def title(self) -> str:
        return _("Containerization")


class RulespecGroupDatasourceProgramsCustom(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "custom"

    @property
    def title(self) -> str:
        return _("Custom integrations")


class RulespecGroupDatasourceProgramsHardware(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "hw"

    @property
    def title(self) -> str:
        return _("Hardware")


class RulespecGroupDatasourceProgramsTesting(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "testing"

    @property
    def title(self) -> str:
        return _("Testing")


class RulespecGroupIntegrateOtherServices(RulespecGroup):
    @property
    def name(self) -> str:
        return "custom_checks"

    @property
    def title(self) -> str:
        return _("Other services")

    @property
    def help(self):
        return _(
            "These services are provided by so called active checks. "
            "You can also integrate custom Nagios plug-ins."
        )


class RulespecGroupActiveChecks(RulespecGroup):
    @property
    def name(self) -> str:
        return "activechecks"

    @property
    def title(self) -> str:
        return _("HTTP, TCP, email, ...")

    @property
    def help(self):
        return _(
            "Rules to add [active_checks|network services] like HTTP and TCP to the "
            "monitoring. The services are provided by so called active checks that allow "
            "you to monitor network services directly from the outside."
        )
