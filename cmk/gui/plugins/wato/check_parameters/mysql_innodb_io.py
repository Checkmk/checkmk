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
from cmk.gui.valuespec import Dictionary, Float, Integer, TextInput, Tuple


def _item_spec_mysql_innodb_io():
    return TextInput(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    )


def _parameter_valuespec_mysql_innodb_io():
    return Dictionary(
        elements=[
            (
                "read",
                Tuple(
                    title=_("Read throughput"),
                    elements=[
                        Float(title=_("warning at"), unit=_("MB/s")),
                        Float(title=_("critical at"), unit=_("MB/s")),
                    ],
                ),
            ),
            (
                "write",
                Tuple(
                    title=_("Write throughput"),
                    elements=[
                        Float(title=_("warning at"), unit=_("MB/s")),
                        Float(title=_("critical at"), unit=_("MB/s")),
                    ],
                ),
            ),
            (
                "average",
                Integer(
                    title=_("Average"),
                    help=_(
                        "When averaging is set, a floating average value "
                        "of the disk throughput is computed and the levels for read "
                        "and write will be applied to the average instead of the current "
                        "value."
                    ),
                    minvalue=1,
                    default_value=5,
                    unit=_("minutes"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_innodb_io",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_innodb_io,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mysql_innodb_io,
        title=lambda: _("MySQL InnoDB Throughput"),
    )
)
