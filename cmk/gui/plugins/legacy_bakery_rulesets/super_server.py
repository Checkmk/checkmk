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


def _valuespec_super_server() -> DropdownChoice[str]:
    return DropdownChoice(
        title=_("Checkmk agent network service (Linux)"),
        help=_(
            "The Checkmk agent does not listen on its own for incoming network connections"
            " on Linux systems. By default it makes use of so called super servers, which are"
            " listening on the network and dispatch incoming requests to applications like"
            " the Checkmk agent. Baked agent packages come with service configurations for"
            " systemd and xinetd, preferring systemd. If you want to choose a specific super"
            " server, you can configure this rule. Optionally disable service installation"
            " completely, e.g. if you connect to the agent via SSH.\n"
            "Please note: The configured/determined service configuration will only get"
            " activated if the super server is compatible to a possibly configured IP restriction"
            ' ruleset. See ruleset "%s".'
        )
        % _("Allowed agent access via IP address"),
        default_value="auto",
        choices=[
            ("auto", _("Prefer systemd, fallback to xinetd if xinetd is available")),
            ("xinetd", _("Install and activate xinetd service")),
            ("systemd", _("Install and activate systemd service")),
            ("no_service", _("Don't install Checkmk service")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("super_server"),
        valuespec=_valuespec_super_server,
    )
)
