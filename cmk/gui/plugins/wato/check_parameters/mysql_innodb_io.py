#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Filesize, Integer, TextInput, Tuple


def _item_spec_mysql_innodb_io() -> TextInput:
    return TextInput(
        title=_("Instance"),
        help=_("Only needed if you have multiple MySQL instances on one server"),
    )


def _parameter_valuespec_mysql_innodb_io() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "read_bytes",
                Tuple(
                    title=_("Read throughput"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "write_bytes",
                Tuple(
                    title=_("Write throughput"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
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
        title=lambda: _("MySQL InnoDB throughput"),
    )
)
