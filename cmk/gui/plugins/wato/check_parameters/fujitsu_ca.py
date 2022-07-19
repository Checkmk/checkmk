#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, DualListChoice, ListOfStrings


def _valuespec_inventory_fujitsu_ca_ports():
    return Dictionary(
        title=_("Fujitsu storage CA port discovery"),
        elements=[
            ("indices", ListOfStrings(title=_("CA port indices"))),
            (
                "modes",
                DualListChoice(
                    title=_("CA port modes"),
                    choices=[
                        ("CA", _("CA")),
                        ("RA", _("RA")),
                        ("CARA", _("CARA")),
                        ("Initiator", _("Initiator")),
                    ],
                    rows=4,
                    size=30,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_fujitsu_ca_ports",
        valuespec=_valuespec_inventory_fujitsu_ca_ports,
    )
)
