#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_db2() -> Alternative:
    return Alternative(
        title=_("DB2 Databases (Linux, AIX)"),
        help=_(
            "By activating this option you will deploy the "
            "<tt>mk_db2</tt> agent plug-in on your target system."
        ),
        elements=[
            Dictionary(
                title=_("Deploy plug-in for DB2"),
                elements=[
                    (
                        "interval",
                        Age(
                            title=_("Run asynchronously"),
                            label=_("Interval for collecting data"),
                            default_value=300,
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the DB2 plug-in"),
                totext=_("disabled"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        match_type="dict",
        name=RuleGroup.AgentConfig("mk_db2"),
        valuespec=_valuespec_agent_config_mk_db2,
    )
)
