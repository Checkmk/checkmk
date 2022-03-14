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
from cmk.gui.valuespec import Age, Optional, TextInput, Tuple


def _item_spec_db2_backup():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_backup():
    return Optional(
        valuespec=Tuple(
            elements=[
                Age(
                    title=_("Warning at"),
                    display=["days", "hours", "minutes"],
                    default_value=86400 * 14,
                ),
                Age(
                    title=_("Critical at"),
                    display=["days", "hours", "minutes"],
                    default_value=86400 * 28,
                ),
            ],
        ),
        title=_("Specify time since last successful backup"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_backup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_backup,
        parameter_valuespec=_parameter_valuespec_db2_backup,
        title=lambda: _("DB2 Time since last database Backup"),
    )
)
