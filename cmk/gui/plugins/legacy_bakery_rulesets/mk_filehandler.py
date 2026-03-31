#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice


def _valuespec_agent_config_mk_filehandler() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Monitor file handles (Linux)"),
        help=_("Hosts configured via this rule get the <tt>mk_filehandler</tt> plug-in deployed."),
        choices=[
            (True, _("Deploy the mk_filehandler plug-in")),
            (None, _("Do not deploy the mk_filehandler plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name="agent_config:mk_filehandler",
        valuespec=_valuespec_agent_config_mk_filehandler,
    )
)
