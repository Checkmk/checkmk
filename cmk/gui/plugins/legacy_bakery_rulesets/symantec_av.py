#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_symantec_av() -> DropdownChoice[bool | None]:
    return DropdownChoice(
        title=_("Symantec Anti Virus (Linux)"),
        help=_(
            "Here you can deploy a plug-in for monitoring the quarantine queue, tasks and updates of Symantec Anti Virus."
        ),
        choices=[
            (True, _("Deploy Symantec Anti Virus plug-in")),
            (None, _("Do not deploy Symantec Anti Virus plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("symantec_av"),
        valuespec=_valuespec_agent_config_symantec_av,
    )
)
