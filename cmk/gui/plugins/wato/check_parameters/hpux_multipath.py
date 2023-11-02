#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput, Tuple


def _parameter_valuespec_hpux_multipath():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "expected",
                    Tuple(
                        title=_("Expected path situation"),
                        help=_(
                            "This rules sets the expected number of various paths for a multipath LUN "
                            "on HPUX servers"
                        ),
                        elements=[
                            Integer(title=_("Number of active paths")),
                            Integer(title=_("Number of standby paths")),
                            Integer(title=_("Number of failed paths")),
                            Integer(title=_("Number of unopen paths")),
                        ],
                    ),
                )
            ],
            # This has to be optional, as it can not have a default value.
            optional_keys=["expected"],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"expected": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hpux_multipath",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("WWID of the LUN")),
        parameter_valuespec=_parameter_valuespec_hpux_multipath,
        title=lambda: _("HP-UX Multipath Count"),
    )
)
