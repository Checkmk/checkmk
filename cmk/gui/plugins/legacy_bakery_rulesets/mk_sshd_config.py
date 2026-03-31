#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_sshd_config() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("SSH daemon configuration (Linux)"),
        help=_("Deploy the agent plug-in <tt>mk_sshd_config</tt>."),
        choices=[
            (True, _("Deploy the SSH daemon configuration plug-in")),
            (None, _("Do not deploy the SSH daemon configuration plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_sshd_config"),
        valuespec=_valuespec_agent_config_mk_sshd_config,
    )
)
