#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_iptables() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Iptables filter configuration"),
        help=_("Hosts configured via this rule get the <tt>mk_iptables</tt> plug-in deployed."),
        choices=[
            (True, _("Deploy iptables plug-in")),
            (False, _("Do not deploy iptables plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_iptables"),
        valuespec=_valuespec_agent_config_mk_iptables,
    )
)
