#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_iis_app_pool_state() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("MS IIS Application Pool State (Windows)"),
        help=_("This plug-in monitors MS IIS Application Pool States on Windows hosts."),
        choices=[
            (True, _("Deploy plug-in for MS IIS Application Pool States")),
            (False, _("Do not deploy plug-in for MS IIS Application Pool States")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("iis_app_pool_state"),
        valuespec=_valuespec_agent_config_iis_app_pool_state,
    )
)
