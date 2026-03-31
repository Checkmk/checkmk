#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_winperf_if() -> DropdownChoice[str | bool]:
    return DropdownChoice(
        title=_("Network interfaces on Windows"),
        help=_(
            "This plug-in checks the status and performance of network interfaces on Windows. "
            "Use the legacy plug-in for Windows versions without Powershell"
        ),
        choices=[
            ("ps1", _("Deploy powershell plug-in - recommended for Win2k8 upwards")),
            ("bat", _("Deploy batch file plug-in - recommended for WinXP / Win2k upwards")),
            (False, _("Do not deploy plug-in for Windows interfaces")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("winperf_if"),
        valuespec=_valuespec_agent_config_winperf_if,
    )
)
