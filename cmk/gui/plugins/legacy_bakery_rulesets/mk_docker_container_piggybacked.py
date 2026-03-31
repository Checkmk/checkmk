#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_docker_container_piggybacked() -> Alternative:
    return Alternative(
        title=_("Piggybacked Docker containers"),
        help=_('This rule is deprecated. Please use "%s" instead.')
        % _("Docker node and containers"),
        elements=[
            Dictionary(
                title=_("Deploy the Docker container plug-in"),
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
                optional_keys=["interval"],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Docker container plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        is_deprecated=True,
        name=RuleGroup.AgentConfig("mk_docker_container_piggybacked"),
        valuespec=_valuespec_agent_config_mk_docker_container_piggybacked,
    )
)
