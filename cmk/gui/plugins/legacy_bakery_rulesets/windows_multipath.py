#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_windows_multipath() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Windows Multipath"),
        help=_(
            "The Windows Multipath plug-in checks for the number of paths in a MPIO (Microsoft Multipath IO)"
        ),
        choices=[
            (True, _("Deploy Windows Multipath plug-in")),
            (False, _("Do not deploy Windows Multipath plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("windows_multipath"),
        valuespec=_valuespec_agent_config_windows_multipath,
    )
)
