#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_isc_dhcpd() -> DropdownChoice[dict[str, object]]:
    return DropdownChoice(
        title=_("ISC DHCP-Daemon (Linux)"),
        help=_(
            "The plug-in <tt>isc_dhcpd</tt> collects information about a DHCP server daemon on Linux."
        ),
        choices=[
            ({}, _("Deploy ISC DHCP-Daemon plug-in")),
            (None, _("Do not deploy ISC DHCP-Daemon plug-in")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("isc_dhcpd"),
        valuespec=_valuespec_agent_config_isc_dhcpd,
    )
)
