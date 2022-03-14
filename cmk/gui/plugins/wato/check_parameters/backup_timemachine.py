#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_backup_timemachine():
    return Dictionary(
        elements=[
            (
                "age",
                Tuple(
                    title=_("Maximum age of latest timemachine backup"),
                    elements=[
                        Age(title=_("Warning if older than"), default_value=86400),
                        Age(title=_("Critical if older than"), default_value=172800),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="backup_timemachine",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_backup_timemachine,
        title=lambda: _("Timemachine backup age"),
    )
)
