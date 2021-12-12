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
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Float,
    Integer,
    Percentage,
    TextInput,
    Tuple,
)


def _parameter_valuespec_rabbitmq_nodes_filedesc():
    return Dictionary(
        elements=[
            (
                "levels",
                CascadingDropdown(
                    title=_("Levels for file descriptor usage"),
                    choices=[
                        (
                            "fd_perc",
                            _("Percentual levels for used file descriptors"),
                            Tuple(
                                elements=[
                                    Percentage(
                                        title=_("Warning at usage of"),
                                        default_value=80.0,
                                        maxvalue=None,
                                    ),
                                    Percentage(
                                        title=_("Critical at usage of"),
                                        default_value=90.0,
                                        maxvalue=None,
                                    ),
                                ],
                            ),
                        ),
                        (
                            "fd_abs",
                            _("Absolut level for total number of used file descriptors"),
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), unit="descriptors"),
                                    Integer(title=_("Critical at"), unit="descriptors"),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            (
                "fd_open_upper",
                Tuple(
                    title=_("Upper level for file descriptor open attempts"),
                    elements=[
                        Integer(title=_("Warning at"), unit="open attempts"),
                        Integer(title=_("Critical at"), unit="open attempts"),
                    ],
                ),
            ),
            (
                "fd_open_rate_upper",
                Tuple(
                    title=_("Upper level for file descriptor open attempts rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "fd_open_rate_lower",
                Tuple(
                    title=_("Lower level for file descriptor open attempts rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_nodes_filedesc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_nodes_filedesc,
        title=lambda: _("RabbitMQ nodes filedescriptors"),
    )
)
