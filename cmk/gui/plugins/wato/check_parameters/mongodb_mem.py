#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Filesize, Tuple


def _parameter_valuespec_mongodb_mem():
    return Dictionary(
        title=_("MongoDB Memory"),
        elements=[
            (
                "resident_levels",
                Tuple(
                    title=_("Resident memory usage"),
                    help=_(
                        "The value of resident is roughly equivalent to the amount of RAM, "
                        "currently used by the database process. In normal use this value tends to grow. "
                        "In dedicated database servers this number tends to approach the total amount of system memory."
                    ),
                    elements=[
                        Filesize(title=_("Warning at"), default_value=1 * 1024**3),
                        Filesize(title=_("Critical at"), default_value=2 * 1024**3),
                    ],
                ),
            ),
            (
                "mapped_levels",
                Tuple(
                    title=_("Mapped memory usage"),
                    help=_(
                        "The value of mapped shows the amount of mapped memory by the database. "
                        "Because MongoDB uses memory-mapped files, this value is likely to be to be "
                        "roughly equivalent to the total size of your database or databases."
                    ),
                    elements=[
                        Filesize(title=_("Warning at"), default_value=1 * 1024**3),
                        Filesize(title=_("Critical at"), default_value=2 * 1024**3),
                    ],
                ),
            ),
            (
                "virtual_levels",
                Tuple(
                    title=_("Virtual memory usage"),
                    help=_(
                        "Virtual displays the quantity of virtual memory used by the mongod process. "
                    ),
                    elements=[
                        Filesize(title=_("Warning at"), default_value=2 * 1024**3),
                        Filesize(title=_("Critical at"), default_value=4 * 1024**3),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mongodb_mem",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_mem,
        title=lambda: _("MongoDB Memory"),
    )
)
