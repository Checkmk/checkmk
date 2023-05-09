#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_msexch_copyqueue():
    return TextAscii(
        title=_("Database Name"),
        help=_("The database name on the Mailbox Server."),
    )


def _parameter_valuespec_msexch_copyqueue():
    return Tuple(
        title=_("Upper Levels for CopyQueue Length"),
        help=_("This rule sets upper levels to the number of transaction logs waiting to be copied "
               "and inspected on your Exchange Mailbox Servers in a Database Availability Group "
               "(DAG). This is also known as the CopyQueue length."),
        elements=[Integer(title=_("Warning at")),
                  Integer(title=_("Critical at"))],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msexch_copyqueue",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msexch_copyqueue,
        parameter_valuespec=_parameter_valuespec_msexch_copyqueue,
        title=lambda: _("MS Exchange DAG CopyQueue"),
    ))
