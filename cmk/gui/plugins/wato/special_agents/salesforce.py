#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListOfStrings


def _valuespec_special_agents_salesforce():
    return Dictionary(
        title=_("Salesforce"),
        help=_("This rule selects the special agent for Salesforce."),
        elements=[
            (
                "instances",
                ListOfStrings(
                    title=_("Instances"),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        help_func=lambda: _("This rule selects the special agent for Salesforce."),
        name="special_agents:salesforce",
        title=lambda: _("Salesforce"),
        valuespec=_valuespec_special_agents_salesforce,
    )
)
