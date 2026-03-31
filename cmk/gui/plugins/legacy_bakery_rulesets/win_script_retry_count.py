#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_script_retry_count() -> Dictionary:
    return Dictionary(
        title=_("Set retry count for plug-ins and local checks"),
        help=_(
            "If set, the plug-in may be called repeately - up to this many "
            "times or until it finishes successfully."
        ),
        elements=[
            (
                "type",
                DropdownChoice(
                    title=_("Type"),
                    help=_("Choose if this rule applies to plug-ins or local checks"),
                    choices=[
                        ("plugin", _("Plug-in")),
                        ("local", _("Local")),
                    ],
                ),
            ),
            (
                "pattern",
                TextInput(
                    title=_("Script Pattern"),
                    help=_(
                        "The pattern (wildcards supported) by which to select the affected scripts."
                    ),
                    allow_empty=False,
                    default_value="*",
                ),
            ),
            (
                "retry_count",
                Integer(
                    title=_("Retry Count"),
                    default_value=0,
                    help=_("Number of retries (not counting the initial regular run)"),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        match_type="all",
        name=RuleGroup.AgentConfig("win_script_retry_count"),
        valuespec=_valuespec_agent_config_win_script_retry_count,
    )
)
