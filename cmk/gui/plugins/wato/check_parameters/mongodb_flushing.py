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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_mongodb_flushing():
    return Dictionary(
        elements=[
            (
                "average_time",
                Tuple(
                    title=_("Average flush time"),
                    elements=[
                        Integer(title=_("Warning at"), unit="ms", default_value=50),
                        Integer(title=_("Critical at"), unit="ms", default_value=100),
                        Integer(title=_("Time interval"), unit="minutes", default_value=10),
                    ],
                ),
            ),
            (
                "last_time",
                Tuple(
                    title=_("Last flush time"),
                    elements=[
                        Integer(title=_("Warning at"), unit="ms", default_value=50),
                        Integer(title=_("Critical at"), unit="ms", default_value=100),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mongodb_flushing",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_flushing,
        title=lambda: _("MongoDB Flushes"),
    )
)
