#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, FixedValue, ListOfStrings, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_dnsclient() -> Alternative:
    return Alternative(
        title=_("Local DNS resolving (Linux, Unix)"),
        help=_(
            "This plug-in tests the local DNS resolver by looking up one "
            "or several host names using <tt>nslookup</tt>. That tool is expected "
            "to be installed on the target machine."
        ),
        elements=[
            ListOfStrings(
                title=_("Host names to resolve"),
                allow_empty=False,
                valuespec=TextInput(
                    regex="^[-a-zA-Z0-9._]*$",
                    regex_error=_("Your host name has an invalid format."),
                    allow_empty=False,
                ),
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the DNS client plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("dnsclient"),
        valuespec=_valuespec_agent_config_dnsclient,
    )
)
