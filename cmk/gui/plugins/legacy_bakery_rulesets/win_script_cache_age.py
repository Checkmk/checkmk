#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_script_cache_age() -> Dictionary:
    return Dictionary(
        title=_("Set cache age for plug-ins and local checks"),
        help=_(
            "A cache age limit on plug-ins and local checks. If set, the output of plug-ins "
            "is cached and reused until this much time has passed."
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
                "cache_age",
                Integer(
                    title=_("Max Cache Age"),
                    unit=_("Seconds"),
                    default_value=0,
                    help=_(
                        "If this is set, the plug-in output will be cached and will only "
                        "be refreshed once the age of the cache has exceeded "
                        "this value."
                    ),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        match_type="all",
        name=RuleGroup.AgentConfig("win_script_cache_age"),
        valuespec=_valuespec_agent_config_win_script_cache_age,
    )
)
