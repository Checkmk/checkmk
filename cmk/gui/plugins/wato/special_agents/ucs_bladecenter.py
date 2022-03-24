#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, FixedValue, Password, TextInput


def _valuespec_special_agents_ucs_bladecenter():
    return Dictionary(
        title=_("UCS Bladecenter"),
        help=_(
            "This rule selects the UCS Bladecenter agent instead of the normal Check_MK Agent "
            "which collects the data through the UCS Bladecenter Web API"
        ),
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
                Password(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
            (
                "no_cert_check",
                FixedValue(
                    value=True,
                    title=_("Disable SSL certificate validation"),
                    totext=_("SSL certificate validation is disabled"),
                ),
            ),
        ],
        optional_keys=["no_cert_check"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ucs_bladecenter",
        valuespec=_valuespec_special_agents_ucs_bladecenter,
    )
)
