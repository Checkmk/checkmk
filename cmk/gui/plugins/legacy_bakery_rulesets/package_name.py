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
from cmk.gui.valuespec import TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_package_name() -> TextInput:
    return TextInput(
        label=_("Package name:"),
        default_value="check-mk-agent",
        regex="^[a-zA-Z][-a-zA-Z0-9]*$",
        regex_error=_(
            "A package must only consist of letters, digits, dash and it must start with a letter."
        ),
        title=_("Name of agent packages (Linux, Unix)"),
        help=_(
            "Choose a custom name for the baked Checkmk agent package, other than default "
            "<tt>check-mk-agent</tt>. Please note that this rule only affects the name "
            "that is used by the package manager (e.g., RPM) to identify the Checkmk agent package, "
            "rather than the contents of the package, e.g., service names. "
            "In particular, it doesn't support to install multiple agents on one machine."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("package_name"),
        valuespec=_valuespec_agent_config_package_name,
    )
)
