#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, TextInput


def _valuespec_special_agents_hp_msa():
    return Dictionary(
        elements=[
            (
                "username",
                TextInput(
                    title=_("Username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                IndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=False,
        title=_("HP MSA via Web Interface"),
        help=_(
            "This rule selects the Agent HP MSA instead of the normal Check_MK Agent "
            "which collects the data through the HP MSA web interface"
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:hp_msa",
        valuespec=_valuespec_special_agents_hp_msa,
    )
)
