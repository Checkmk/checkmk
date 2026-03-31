#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mcafee_av_client() -> DropdownChoice[bool]:
    return DropdownChoice(
        title=_("McAfee AV client"),
        help=_(
            "This plug-in monitors the signature date of a Windows "
            "system using McAfee Anti-Virus software"
        ),
        choices=[
            (True, _("Deploy Windows McAfee AV client plug-in")),
            (None, _("Do not deploy Windows McAfee AV client plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("mcafee_av_client"),
        valuespec=_valuespec_agent_config_mcafee_av_client,
    )
)
