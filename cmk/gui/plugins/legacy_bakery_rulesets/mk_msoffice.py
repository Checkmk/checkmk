#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, TextInput
from cmk.gui.wato import IndividualOrStoredPassword
from cmk.ruleset_matcher.definition import RuleGroup


def _valuespec_agent_config_mk_msoffice() -> Alternative:
    return Alternative(
        title=_("MS Office 365 (Windows)"),
        help=_(
            "This plug-in can be used to collect information of all MS Office 365 licenses and serviceplans "
            "using the MgGraph PowerShell module."
        ),
        elements=[
            Dictionary(
                title=_("Deploy MS Office 365 plug-in"),
                elements=[
                    ("client_id", TextInput(title=_("ClientID"), allow_empty=False)),
                    ("tenant_id", TextInput(title=_("TenantId"), allow_empty=False)),
                    (
                        "client_secret",
                        IndividualOrStoredPassword(
                            title=_("ClientSecret"),
                            help=_(
                                "Enter the client secret explicitly or select one from the password store."
                            ),
                            allow_empty=False,
                        ),
                    ),
                ],
                required_keys=["client_id", "tenant_id", "client_secret"],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy plug-in for MS Office 365"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_msoffice"),
        valuespec=_valuespec_agent_config_mk_msoffice,
    )
)
