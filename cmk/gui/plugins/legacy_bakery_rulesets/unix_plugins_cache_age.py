#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_unix_plugins_cache_age() -> Dictionary:
    return Dictionary(
        title=_("Set cache age for plug-ins (Linux, Unix)"),
        help=_(
            "A cache age limit on plug-ins. If set, the output of plug-ins is cached and reused until this much time has passed. Especially, this rule can be used to enable caching for plug-ins that are lacking this option in their dedicated rule set."
        ),
        elements=[
            (
                "override",
                DropdownChoice(
                    title=_("Priority"),
                    help=_(
                        "Choose whether this rule gets "
                        "prioritized over cache times that are configured in the plug-in's "
                        'dedicated rules. Please choose "override" only if you know what '
                        "you're doing, because some plug-ins have minimum cache times for "
                        "performance or other reasons, that will also get overridden by this "
                        "setting."
                    ),
                    choices=[
                        (False, _("Preserve cache times configured by other rules")),
                        (True, _("Override cache times configured by other rules")),
                    ],
                ),
            ),
            (
                "pattern",
                TextInput(
                    title=_("Plug-in file pattern"),
                    help=_(
                        "The global pattern by which to select the affected "
                        "plug-ins. It is applied to the file names of the "
                        "agent plug-in files as they appear within the "
                        "agent package."
                    ),
                    allow_empty=False,
                    default_value="*",
                ),
            ),
            (
                "interval",
                Integer(
                    title=_("Max cache age (interval)"),
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
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        match_type="all",
        name=RuleGroup.AgentConfig("unix_plugins_cache_age"),
        valuespec=_valuespec_agent_config_unix_plugins_cache_age,
    )
)
