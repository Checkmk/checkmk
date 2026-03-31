#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
)
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_super_server_solaris() -> DropdownChoice[str]:
    return DropdownChoice(
        title=_("Checkmk agent network service (Solaris)"),
        help=_(
            "The Checkmk agent does not listen on its own for incoming network connections."
            " By default it makes use of so called super servers, which are"
            " listening on the network and dispatch incoming requests to applications like"
            " the Checkmk agent. Baked agent packages for Solaris come with an"
            " installation script for an inetd service."
            " With this rule, you can optionally disable the service installation"
            " , e.g., if you connect to the agent via SSH.\n"
        ),
        default_value="inetd",
        choices=[
            ("inetd", _("Install and activate inetd service")),
            ("no_service", _("Don't install Checkmk service")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("super_server_solaris"),
        valuespec=_valuespec_super_server_solaris,
    )
)
