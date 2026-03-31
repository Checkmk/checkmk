#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_dmidecode() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("System information for inventory via dmidecode (Windows)"),
        help=_(
            r"This plug-in requires the executable <tt>C:\Programme\GnuWin32\sbin\dmidecode.exe</tt>. "
            "This is the default location when installing this tool. You can download it for free "
            "from <a href='http://gnuwin32.sourceforge.net/packages/dmidecode.htm'>here</a>. "
        ),
        choices=[
            (True, _("Deploy plug-in for Windows system info")),
            (None, _("Do not deploy plug-in for Windows system info")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("win_dmidecode"),
        valuespec=_valuespec_agent_config_win_dmidecode,
    )
)
