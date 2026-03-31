#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_service() -> Dictionary:
    return Dictionary(
        title=_("Checkmk Windows agent service settings"),
        elements=[
            (
                "restart_on_crash",
                DropdownChoice(
                    title=_("Auto Restart on Crash"),
                    help=_(
                        "Use this rule set to enable or disable automatic service restarts on crash "
                        "or other internal errors."
                    ),
                    choices=[
                        ("yes", _("Windows Service restarts automatically")),
                        ("no", _("Windows Service doesn't restart automatically")),
                    ],
                    default_value="yes",
                ),
            ),
            (
                "error_mode",
                DropdownChoice(
                    title=_("Action on Error"),
                    help=_(
                        "Use this rule set to control some actions which can be performed "
                        "upon crash or other problems."
                    ),
                    choices=[
                        ("log", _("Windows Service writes information to the Event Log")),
                        ("ignore", _("Windows Service does nothing")),
                    ],
                    default_value="log",
                ),
            ),
            (
                "start_mode",
                DropdownChoice(
                    title=_("Service start type"),
                    help=_(
                        "Use this rule set to choose a desirable start mode of the Windows "
                        "service. You may also prevent the service from starting."
                    ),
                    choices=[
                        ("auto", _("Windows Service starts automatically")),
                        ("delayed", _("Windows Service starts automatically with delay")),
                        ("demand", _("Windows Service starts on demand")),
                        ("disabled", _("Windows Service is disabled and can't be started")),
                    ],
                    default_value="auto",
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_service"),
        valuespec=_valuespec_agent_config_win_service,
    )
)
