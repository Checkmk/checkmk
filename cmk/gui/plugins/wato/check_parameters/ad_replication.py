#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput, Tuple


def _item_spec_ad_replication():
    return TextInput(
        title=_("Replication Partner"),
        help=_("The name of the replication partner (Destination DC Site/Destination DC)."),
    )


def _parameter_valuespec_ad_replication() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "failure_levels",
                    Tuple(
                        help=_("Upper levels for the number of replication failures"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("failures")),
                            Integer(title=_("Critical at"), unit=_("failures")),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"failure_levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ad_replication",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_ad_replication,
        parameter_valuespec=_parameter_valuespec_ad_replication,
        title=lambda: _("Active Directory Replication"),
    )
)
