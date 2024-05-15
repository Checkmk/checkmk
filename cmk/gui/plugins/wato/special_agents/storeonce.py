#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_storeonce():
    return Dictionary(
        title=_("HPE StoreOnce"),
        help=_(
            "This rule set selects the special agent for HPE StoreOnce Applainces "
            "instead of the normal Checkmk agent and allows monitoring via Web API. "
        ),
        optional_keys=["cert"],
        elements=[
            ("user", TextInput(title=_("Username"), allow_empty=False)),
            (
                "password",
                MigrateToIndividualOrStoredPassword(title=_("Password"), allow_empty=False),
            ),
            (
                "cert",
                DropdownChoice(
                    title=_("SSL certificate verification"),
                    choices=[
                        (True, _("Activate")),
                        (False, _("Deactivate")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("storeonce"),
        valuespec=_valuespec_special_agents_storeonce,
    )
)
