#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common_tls_verification import tls_verify_flag_default_yes
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)


def _valuespec_special_agents_innovaphone() -> Dictionary:
    return Dictionary(
        title=_("Innovaphone Gateways"),
        help=_("Please specify the user and password needed to access the xml interface"),
        elements=[
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            ),
            tls_verify_flag_default_yes(),
            (
                "auth_basic",
                Dictionary(
                    elements=[
                        (
                            "username",
                            TextInput(
                                title=_("Login username"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "password",
                            MigrateToIndividualOrStoredPassword(
                                title=_("Password"),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=[],
                    title=_("Basic authentication"),
                ),
            ),
        ],
        optional_keys=["protocol", "no-cert-check"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("innovaphone"),
        valuespec=_valuespec_special_agents_innovaphone,
    )
)
