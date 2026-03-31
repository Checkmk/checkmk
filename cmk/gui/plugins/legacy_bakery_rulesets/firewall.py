#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_firewall() -> Dictionary:
    return Dictionary(
        title=_("Windows Firewall"),
        elements=[
            (
                "mode",
                DropdownChoice(
                    title=_("Mode"),
                    label=_("Manage Windows firewall rules for Checkmk agent"),
                    help=_(
                        "Use this rule set to automatically configure the firewall rules that are "
                        "needed to communicate with the Checkmk Windows agent on the monitored "
                        "Windows hosts."
                    ),
                    choices=[
                        ("none", _("Do not configure Windows Firewall")),
                        ("remove", _("Remove Windows Firewall configuration if present")),
                        ("configure", _("Configure Windows Firewall to allow host monitoring")),
                    ],
                    default_value="configure",
                ),
            ),
            (
                "port",
                DropdownChoice(
                    title=_("Port"),
                    label=_("Ports to open"),
                    help=_(
                        "This setting determines how ports will be enabled in Windows Firewall."
                    ),
                    choices=[
                        ("auto", _("Required port")),
                        ("all", _("All ports")),
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
        name=RuleGroup.AgentConfig("firewall"),
        valuespec=_valuespec_agent_config_firewall,
    )
)
