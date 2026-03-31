#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_scaleio() -> Alternative:
    return Alternative(
        title=_("EMC ScaleIO"),
        elements=[
            Dictionary(
                title=_("Deploy the Checkmk EMC ScaleIO plug-in"),
                elements=[
                    ("user", TextInput(title=_("Username"))),
                    ("password", MigrateToIndividualOrStoredPassword(title=_("Password"))),
                    ("interval", Age(title=_("Interval for collecting data"), default_value=60)),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Checkmk EMC ScaleIO plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_scaleio"),
        valuespec=_valuespec_agent_config_mk_scaleio,
    )
)
