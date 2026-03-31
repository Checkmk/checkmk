#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    ListOf,
    ListOfStrings,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_site_object_counts() -> Alternative:
    return Alternative(
        title=_("Checkmk site objects"),
        help=_(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_site_object_counts</tt>. "
            "The plug-in runs below the specified user's environment. Furthermore you have to "
            "determine host tags or service check commands."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the Checkmk object counts plug-in"),
                elements=[
                    (
                        "tags",
                        ListOfStrings(
                            title=_("Tags"),
                            orientation="horizontal",
                        ),
                    ),
                    (
                        "service_check_commands",
                        ListOfStrings(
                            title=_("Service check commands"),
                            orientation="horizontal",
                        ),
                    ),
                    (
                        "sites",
                        ListOf(
                            valuespec=Tuple(
                                elements=[
                                    TextInput(
                                        title=_("Site name"),
                                    ),
                                    ListOfStrings(
                                        title=_("Tags"),
                                        orientation="horizontal",
                                    ),
                                    ListOfStrings(
                                        title=_("Service check commands"),
                                        orientation="horizontal",
                                    ),
                                ]
                            ),
                            title=_("Sites"),
                        ),
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Checkmk site objects plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_site_object_counts"),
        valuespec=_valuespec_agent_config_mk_site_object_counts,
    )
)
