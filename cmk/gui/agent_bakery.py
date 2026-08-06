#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.i18n import _
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringAgents
from cmk.gui.watolib.rulespecs import RulespecGroup, RulespecSubGroup


class RulespecGroupMonitoringAgentsLinuxUnixAgent(RulespecSubGroup):
    @property
    @override
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    @override
    def sub_group_name(self) -> str:
        return "linux_agent"

    @property
    @override
    def title(self) -> str:
        return _("Linux/UNIX agent options")


class RulespecGroupMonitoringAgentsWindowsAgent(RulespecSubGroup):
    @property
    @override
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    @override
    def sub_group_name(self) -> str:
        return "windows_agent"

    @property
    @override
    def title(self) -> str:
        return _("Windows agent options")


class RulespecGroupMonitoringAgentsAgentPlugins(RulespecSubGroup):
    @property
    @override
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    @override
    def sub_group_name(self) -> str:
        return "agent_plugins"

    @property
    @override
    def title(self) -> str:
        return _("Agent plug-ins")


class RulespecGroupMonitoringAgentsAutomaticUpdates(RulespecSubGroup):
    @property
    @override
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    @override
    def sub_group_name(self) -> str:
        return "automatic_updates"

    @property
    @override
    def title(self) -> str:
        return _("Automatic updates")
