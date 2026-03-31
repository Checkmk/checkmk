#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_lnx_quota() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("User quotas on file systems (Linux)"),
        help=_(
            "Hosts configured via this rule get the <tt>lnx_quota</tt> plug-in deployed. This is only useful if you have file system quotas setup on the host."
        ),
        choices=[
            (True, _("Deploy Linux file system quota plug-in")),
            (None, _("Do not deploy Linux file system quota plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("lnx_quota"),
        valuespec=_valuespec_agent_config_lnx_quota,
    )
)
