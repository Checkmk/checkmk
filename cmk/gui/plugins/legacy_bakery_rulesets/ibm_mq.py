#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, DropdownChoice, FixedValue, ListOfStrings
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_ibm_mq() -> Alternative:
    return Alternative(
        title=_("IBM MQ (Linux)"),
        help=_("This plug-in monitors channels, managers and queues of IBM MQ."),
        elements=[
            Dictionary(
                title=_("Deploy IBM MQ plug-in"),
                elements=[
                    (
                        "only_qm",
                        ListOfStrings(
                            title=_("Queues to monitor"),
                            allow_empty=False,
                            help=_("Only queues explicitly listed here will be monitored."),
                        ),
                    ),
                    (
                        "skip_qm",
                        ListOfStrings(
                            title=_("Queues to be skipped"),
                            allow_empty=False,
                            help=_("All queues listed here will be skipped."),
                        ),
                    ),
                    (
                        "execute_as_another_user",
                        DropdownChoice(
                            title=_("Execute as another user"),
                            choices=[("mqm", _("Execute as MQM"))],
                            default="mqm",
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the IBM MQ plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("ibm_mq"),
        valuespec=_valuespec_agent_config_ibm_mq,
    )
)
