#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_db2_mem() -> DropdownChoice[bool | None]:
    return DropdownChoice(
        title=_("Memory usage of DB2 (Linux, AIX, Solaris)"),
        help=_(
            "Hosts configured via this rule get the plug-in <tt>db2_mem</tt> "
            "deployed. This will create one service for the memory consumption "
            "of every running DB2 instance found on the system."
        ),
        choices=[
            (True, _("Deploy DB2 memory plug-in")),
            (None, _("Do not deploy DB2 memory plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("db2_mem"),
        valuespec=_valuespec_agent_config_db2_mem,
    )
)
