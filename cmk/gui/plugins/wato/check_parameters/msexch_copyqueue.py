#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput


def _item_spec_msexch_copyqueue() -> TextInput:
    return TextInput(
        title=_("Database name"),
        help=_("The database name on the Mailbox Server."),
    )


def _parameter_valuespec_msexch_copyqueue() -> Migrate[dict[str, Any]]:
    return Migrate(
        valuespec=Dictionary(
            help=_(
                "This rule sets upper levels to the number of transaction logs waiting to be copied "
                "and inspected on your Exchange Mailbox Servers in a Database Availability Group "
                "(DAG). This is also known as the CopyQueue length."
            ),
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Upper levels for CopyQueue length"),
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msexch_copyqueue",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msexch_copyqueue,
        parameter_valuespec=_parameter_valuespec_msexch_copyqueue,
        title=lambda: _("MS Exchange DAG CopyQueue"),
    )
)
