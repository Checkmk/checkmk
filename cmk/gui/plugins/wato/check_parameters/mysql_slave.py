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
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _item_spec_mysql_slave():
    return TextInput(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    )


def _parameter_valuespec_mysql_slave():
    return Dictionary(
        elements=[
            (
                "seconds_behind_master",
                Tuple(
                    title=_("Max. time behind the master"),
                    help=_(
                        "Compares the time which the slave can be behind the master. "
                        "This rule makes the check raise warning/critical states if the time is equal to "
                        "or above the configured levels."
                    ),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_slave",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_slave,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mysql_slave,
        title=lambda: _("MySQL Slave"),
    )
)
