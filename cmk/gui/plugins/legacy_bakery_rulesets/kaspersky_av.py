#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_kaspersky_av() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Kaspersky Anti-Virus (Linux)"),
        help=_(
            "Here you can deploy a plug-in for monitoring the quarantine queue, tasks and updates of Kaspersky Anti Virus."
        ),
        choices=[
            (True, _("Deploy Kaspersky Anti-Virus plug-in")),
            (None, _("Do not deploy Kaspersky Anti-Virus plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("kaspersky_av"),
        valuespec=_valuespec_agent_config_kaspersky_av,
    )
)
