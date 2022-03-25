#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, Password, TextInput


def _valuespec_special_agents_storeonce():
    return Dictionary(
        title=_("HPE StoreOnce"),
        help=_(
            "This rule set selects the special agent for HPE StoreOnce Applainces "
            "instead of the normal Check_MK agent and allows monitoring via Web API. "
        ),
        optional_keys=["cert"],
        elements=[
            ("user", TextInput(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
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
        name="special_agents:storeonce",
        valuespec=_valuespec_special_agents_storeonce,
    )
)
