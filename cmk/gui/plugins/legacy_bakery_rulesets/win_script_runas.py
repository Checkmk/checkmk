#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.valuespec import Alternative, Dictionary, DropdownChoice, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_runas() -> Alternative:
    return Alternative(
        title=_("Run plug-ins and local checks using non-system account"),
        help=_(
            "The rule gives the possibility to run any script "
            "using a given user account. There are two modes of the rule: "
            "<i>group mode</i>, in the case Windows Agent provides its own internal "
            "user in the requested group to run the script, or <i>user mode</i>, "
            "in this case you should specify the full credentials. The <i>group "
            "mode</i> is more secure, because no credentials need to be stored anywhere, "
            "except in the agent internally. When using the <i>user mode</i>, "
            "the provided credentials are <b>stored in plain text</b> on all Checkmk servers "
            "to which the configuration is applied. The credentials (in plain text) will also "
            "be baked into the Agent Bakery packages, distributed and installed with "
            "them on the target system. "
            "We highly recommend to use the <i>group mode</i> whenever possible."
        ),
        elements=[
            Dictionary(
                title=_("Enable 'Run As <b>Local Group</b>' for scripts"),
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
                            title=_("Script pattern"),
                            help=_(
                                "The pattern (wildcards supported) to select the affected scripts."
                            ),
                            allow_empty=False,
                            default_value="*",
                        ),
                    ),
                    (
                        "group",
                        TextInput(
                            title=_("Local group name"),
                            help=_("Enter group"),
                            allow_empty=False,
                            default_value="Users",
                        ),
                    ),
                ],
                optional_keys=[],
            ),
            Dictionary(
                title=_("Enable 'Run As <b>User</b>' for scripts"),
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
                            title=_("Script pattern"),
                            help=_(
                                "The pattern (wildcards supported) to select the affected scripts."
                            ),
                            allow_empty=False,
                            default_value="*",
                        ),
                    ),
                    (
                        "user",
                        TextInput(
                            title=_("Username"),
                            help=_("Enter username"),
                            allow_empty=False,
                            default_value="?",
                        ),
                    ),
                    (
                        "password",
                        MigrateToIndividualOrStoredPassword(
                            title=_("User password"),
                            help=_("Enter user password"),
                            allow_empty=False,
                        ),
                    ),
                ],
                optional_keys=[],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        match_type="all",
        name=RuleGroup.AgentConfig("win_script_runas"),
        valuespec=_valuespec_agent_config_win_runas,
    )
)
