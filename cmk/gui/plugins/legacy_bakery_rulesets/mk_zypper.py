#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, FixedValue
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_zypper() -> Alternative:
    return Alternative(
        title=_("Zypper normal and security updates (Linux)"),
        help=_(
            "This will deploy the agent plug-in <tt>mk_zypper</tt>. This will activate the "
            "check <tt>zypper</tt> on SUSE Linux hosts and monitor normal and security updates."
        ),
        elements=[
            Age(
                title=_("Deploy the Zypper plug-in"),
                label=_("Interval for checking for updates:"),
            ),
            FixedValue(
                value=None, title=_("Do not deploy the Zypper plug-in"), totext=_("(disabled)")
            ),
        ],
        default_value=14400,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_zypper"),
        valuespec=_valuespec_agent_config_mk_zypper,
    )
)
