#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecGroupMonitoringAgents,
    RulespecSubGroup,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


class RulespecGroupMonitoringAgentsWindowsModules(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupMonitoringAgents

    @property
    def sub_group_name(self) -> str:
        return "windows_modules"

    @property
    def title(self) -> str:
        return _("Windows Modules")  # and Custom files in the future


rulespec_group_registry.register(RulespecGroupMonitoringAgentsWindowsModules)


def _valuespec_agent_install_python() -> Dictionary:
    return Dictionary(
        title=_("Install Python runtime environment"),
        elements=[
            (
                "installation",
                DropdownChoice(
                    title=_("Installation"),
                    help=_(
                        "This rule set allows to add embedded Python "
                        "to the Windows agent installation. "
                    ),
                    choices=[
                        (
                            "auto",
                            _("Install Python automatically when configured plug-ins need it"),
                        ),
                        ("install", _("Always install Python with agent")),
                        ("no_install", _("Never install Python with the agent")),
                    ],
                    default_value="auto",
                ),
            ),
            (
                "usage",
                DropdownChoice(
                    title=_("Usage"),
                    help=_(
                        "This rule set allows to choose which Python interpreter is used "
                        "to run Python scripts."
                    ),
                    choices=[
                        ("auto", _("Use Checkmk Python, if it has been installed")),
                        ("system", _("Do not use Checkmk Python, even if it has been installed")),
                    ],
                    default_value="auto",
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsModules,
        name=RuleGroup.AgentConfig("install_python"),
        valuespec=_valuespec_agent_install_python,
    )
)
