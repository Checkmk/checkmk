#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_suseconnect() -> DropdownChoice[bool]:
    return DropdownChoice[bool](
        title=_("SUSEConnect (Linux)"),
        help=_("Deploy the agent plug-in <tt>mk_suseconnect</tt>."),
        choices=[
            (True, _("Deploy SUSEConnect plug-in")),
            (None, _("Do not deploy SUSEConnect plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_suseconnect"),
        valuespec=_valuespec_agent_config_mk_suseconnect,
    )
)
