#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mailman_lists() -> DropdownChoice[dict[str, object]]:
    return DropdownChoice(
        title=_("Mailman mailing lists queues (Linux)"),
        help=_("The plug-in <tt>mailman3_lists</tt> (Mailman 3) monitors Mailman mailing lists."),
        choices=[
            ({}, _("Deploy Mailman plug-in")),
            (None, _("Do not deploy Mailman plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mailman_lists"),
        valuespec=_valuespec_agent_config_mailman_lists,
    )
)
