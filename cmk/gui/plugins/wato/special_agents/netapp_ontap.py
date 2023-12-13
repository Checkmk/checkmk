#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, ListChoice, TextInput
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_netapp_ontap() -> Dictionary:
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
                MigrateToIndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
            (
                "skip_elements",
                ListChoice(
                    choices=[
                        ("ctr_volumes", _("Do not query volume performance counters")),
                    ],
                    title=_("Performance improvements"),
                    help=_(
                        "Here you can configure whether the performance counters should get queried. "
                        "This can save quite a lot of CPU load on larger systems."
                    ),
                ),
            ),
        ],
        title=_("NetApp via Ontap API"),
        help=_(
            "This rule set selects the NetApp special agent instead of the normal Checkmk Agent "
            "and allows monitoring via the NetApp Ontap REST API."
        ),
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("netapp_ontap"),
        valuespec=_valuespec_special_agents_netapp_ontap,
    )
)
