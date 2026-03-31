#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice, ListOf, TextInput, Tuple
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_runas() -> ListOf[tuple[str, str, str]]:
    return ListOf(
        valuespec=Tuple(
            orientation="horizontal",
            elements=[
                DropdownChoice(
                    title=_("Script Type"),
                    choices=[
                        ("plugin", _("Directory containing agent plug-ins")),
                        ("local", _("Directory containing local checks")),
                        ("mrpe", _("Path to MRPE configuration file")),
                    ],
                ),
                TextInput(
                    title=_("Run as user (empty = agent user):"),
                    size=20,
                ),
                TextInput(
                    title=_("File name / directory"),
                    help=_(
                        "An absolute path to the configuration file (in case of MRPE) or to a"
                        " directory in case of local / plug-in"
                    ),
                    regex="^/",
                    regex_error=_("Please specify an absolute path name"),
                    size=40,
                    allow_empty=False,
                ),
            ],
        ),
        add_label=_("Add new user configuration"),
        title=_("Additional Plug-ins, local checks and MRPE configurations"),
        help=_(
            "This rule set allows you to let users keep their own agent plug-ins, local scripts"
            " and MK Remote Plugin Executor (MRPE) configuration, which will be run by the agent"
            " with the permissions of the specified user."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        match_type="list",
        name=RuleGroup.AgentConfig("runas"),
        valuespec=_valuespec_agent_config_runas,
    )
)
