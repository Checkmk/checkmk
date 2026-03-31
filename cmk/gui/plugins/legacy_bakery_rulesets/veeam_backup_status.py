#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_veeam_backup_status() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Veeam backup status (Windows)"),
        help=_("This plug-in monitors Veeam backup status on Window hosts."),
        choices=[
            (True, _("Deploy plug-in for Veeam backup status")),
            (None, _("Do not deploy plug-in for Veeam backup status")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("veeam_backup_status"),
        valuespec=_valuespec_agent_config_veeam_backup_status,
    )
)
