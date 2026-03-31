#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_cups_queues() -> Alternative:
    return Alternative(
        title=_("CUPS Printer Queues"),
        elements=[
            Dictionary(
                title=_("Deploy the Checkmk CUPS queues plug-in"),
                elements=[
                    (
                        "interval",
                        Age(title=_("Interval for collecting data")),
                    ),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Checkmk CUPS queues plug-in"),
                totext=_("(disabled)"),
            ),
        ],
        default_value={"interval": 60},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_cups_queues"),
        valuespec=_valuespec_agent_config_mk_cups_queues,
    )
)
