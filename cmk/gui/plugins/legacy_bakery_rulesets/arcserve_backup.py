#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_arcserve_backup() -> Alternative:
    return Alternative(
        title=_("Arcserve (German) backups (Windows)"),
        help=_(
            "This plug-in monitors Arcserve backups by deploying a plug-in for the "
            "Arcserve server on Windows. This only supports the German version of "
            "Arcserve, since the log messages are in localized language."
        ),
        elements=[
            Dictionary(
                title=_("Deploy Arcserve plug-in"),
                elements=[
                    (
                        "sqlserver",
                        TextInput(
                            title=_("SQL-Server to connect to"),
                            help=_("Put the name of the database here, e.g. SATURN\\ARCSERVE_DB"),
                            allow_empty=False,
                            regex=r"^[A-Za-z0-9_\\]+$",
                            regex_error=_("You have used an invalid character"),
                        ),
                    ),
                ],
                optional_keys=False,
            ),
            FixedValue(
                value=None, title=_("Do not deploy the Arcserve plug-in"), totext=_("(disabled)")
            ),
        ],
        default_value={"sqlserver": r"SATURN\ARCSERVE_DB"},
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("arcserve_backup"),
        valuespec=_valuespec_agent_config_arcserve_backup,
    )
)
