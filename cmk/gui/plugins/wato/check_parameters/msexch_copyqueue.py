#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _item_spec_msexch_copyqueue():
    return TextInput(
        title=_("Database Name"),
        help=_("The database name on the Mailbox Server."),
    )


def _parameter_valuespec_msexch_copyqueue():
    return Tuple(
        title=_("Upper Levels for CopyQueue Length"),
        help=_(
            "This rule sets upper levels to the number of transaction logs waiting to be copied "
            "and inspected on your Exchange Mailbox Servers in a Database Availability Group "
            "(DAG). This is also known as the CopyQueue length."
        ),
        elements=[Integer(title=_("Warning at")), Integer(title=_("Critical at"))],
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
