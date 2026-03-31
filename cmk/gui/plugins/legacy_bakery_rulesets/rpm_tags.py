#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_rpm_tags() -> Dictionary:
    return Dictionary(
        title=_("Specify RPM package tags (Linux)"),
        help=_(
            "The Linux RPM packages built by the Agent Bakery are packaged independently "
            "of any Linux distribution. Hence, the <tt>DISTRIBUTION</tt> and <tt>DISTTAG</tt> "
            "tags are left empty within the RPM spec file. "
            "Here, you can manually specify these tags."
        ),
        elements=[
            (
                "distribution",
                TextInput(
                    title=("DISTRIBUTION"),
                    allow_empty=False,
                ),
            ),
            (
                "disttag",
                TextInput(
                    title=_("DISTTAG"),
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        name=RuleGroup.AgentConfig("rpm_tags"),
        valuespec=_valuespec_rpm_tags,
    )
)
