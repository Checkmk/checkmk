#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_windows_updates() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("Windows Updates"),
        help=_(
            "The Windows Updates plug-in checks for the number of pending updates. The "
            "default configuration will include the asynchronous execution and caching "
            "of the output for 4 hours (14400 seconds). You can still change these "
            "values with the Setup rule sets <i>Set cache age for plug-ins and local checks"
            "</i> and <i>Set execution mode for plug-ins and local checks</i>."
        ),
        choices=[
            (True, _("Deploy Windows Updates plug-in")),
            (False, _("Do not deploy Windows Updates plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("windows_updates"),
        valuespec=_valuespec_agent_config_windows_updates,
    )
)
