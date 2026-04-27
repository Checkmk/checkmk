#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Age, Alternative, Checkbox, Dictionary, DropdownChoice, FixedValue
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_apt() -> Alternative:
    return Alternative(
        title=_("APT normal and security updates (Linux)"),
        help=_(
            "This will deploy the agent plug-in <tt>mk_apt</tt>. This will activate the "
            "check <tt>apt</tt> on DEB-based hosts (like Debian and Ubuntu) and monitor pending normal and security updates."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the APT plug-in"),
                elements=[
                    (
                        "interval",
                        Age(title="Interval for checking for updates"),
                    ),
                    (
                        "method",
                        DropdownChoice(
                            title=_("Method"),
                            choices=[
                                ("upgrade", _("apt-get upgrade")),
                                ("dist-upgrade", _("apt-get dist-upgrade")),
                            ],
                        ),
                    ),
                    (
                        "update",
                        Checkbox(
                            title=_("Update package database"),
                            label=_("Do an <tt>apt-get update</tt> before the check"),
                        ),
                    ),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None, title=_("Do not deploy the APT plug-in"), totext=_("(disabled)")
            ),
        ],
        default_value={"interval": 86400, "method": "upgrade", "update": True},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_apt"),
        valuespec=_valuespec_agent_config_mk_apt,
    )
)
