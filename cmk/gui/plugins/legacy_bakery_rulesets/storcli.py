#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_storcli() -> Alternative:
    return Alternative(
        title=_("LSI Raid Controller Status (via StorCLI)"),
        help=_(
            "This plug-in collects information on the logical volumes and physical disks "
            "of LSI RAID controllers using the StorCLI utility. StorCLI must be installed "
            "on the target system for this plug-in to work."
        ),
        elements=[
            TextInput(
                title=_("Deploy StorCLI plug-in"),
                default_value=r"C:\Program Files\StorCLI\storcli64.exe",
            ),
            FixedValue(
                value=None, title=_("Do not deploy the StorCLI plug-in"), totext=_("(disabled)")
            ),
        ],
        default_value=None,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("storcli"),
        valuespec=_valuespec_agent_config_storcli,
    )
)
