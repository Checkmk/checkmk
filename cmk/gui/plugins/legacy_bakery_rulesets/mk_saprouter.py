#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_saprouter() -> Alternative:
    return Alternative(
        title=_("SAP router certificate"),
        help=_(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_saprouter</tt>. "
            "The plug-in runs below the specified user's environment. Furthermore you have to "
            "determine the path to sapgenpse. It's recommended to run the plug-in asynchronously."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the SAP router plug-in"),
                elements=[
                    (
                        "user",
                        TextInput(
                            title=_("Username"),
                            allow_empty=False,
                        ),
                    ),
                    (
                        "path",
                        TextInput(
                            title=_("Path to sapgenpse"),
                            allow_empty=False,
                        ),
                    ),
                    (
                        "interval",
                        Age(
                            title=_("Run asynchronously"),
                            label=_("Interval for collecting data"),
                            default_value=86400,
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the SAP router plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_saprouter"),
        valuespec=_valuespec_agent_config_mk_saprouter,
    )
)
