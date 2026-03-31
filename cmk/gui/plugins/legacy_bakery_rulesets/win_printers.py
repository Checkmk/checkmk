#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_printers() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Windows Printer Queues and States"),
        help=_(
            "This plug-in monitors the number of print jobs in the printer queues and the printer states"
        ),
        choices=[
            (True, _("Deploy Windows Printer Queue plug-in")),
            (None, _("Do not deploy Windows Printer Queue plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_printers"),
        valuespec=_valuespec_agent_config_win_printers,
    )
)
