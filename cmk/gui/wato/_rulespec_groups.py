#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfiguration
from cmk.gui.watolib.rulespecs import RulespecGroup, RulespecGroupRegistry, RulespecSubGroup


def register(rulespec_group_registry: RulespecGroupRegistry) -> None:
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
            "discovery or the deactivation of check plugins and services. "
            "Additionally, the discovery of individual check plugins like "
            "for example the interface check plugin can "
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
        return _("Storage, Filesystems and Files")


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
