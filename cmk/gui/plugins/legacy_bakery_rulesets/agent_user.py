#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import ID, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_agent_user() -> TextInput:
    return ID(
        title=_("Run agent as non-root user (Linux) (deprecated)"),
        help=_(
            "This rule set will only set the agent user to the configured value."
            "<br>It will not take care of further needed permissions on the target system."
            "<br>Please use the new rule set <i>Customize agent package</i> instead, which offers"
            " a proper non-root agent installation."
            "<br> When configuring <i>Customize agent package</i>, matching rules from"
            " this rule set will be ignored.<br>"
        ),
        allow_empty=False,
        label=_("Linux user:"),
        default_value="root",
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("agent_user"),
        valuespec=_valuespec_agent_config_agent_user,
        deprecation_planned=True,
    )
)
