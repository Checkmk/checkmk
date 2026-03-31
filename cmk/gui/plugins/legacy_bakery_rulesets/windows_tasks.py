#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_windows_tasks() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Windows task scheduler"),
        help=_("This plug-in checks the last return state of Windows task scripts"),
        choices=[
            (True, _("Deploy plug-in for Windows task scheduler")),
            (None, _("Do not deploy plug-in for Windows task scheduler")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("windows_tasks"),
        valuespec=_valuespec_agent_config_windows_tasks,
    )
)
