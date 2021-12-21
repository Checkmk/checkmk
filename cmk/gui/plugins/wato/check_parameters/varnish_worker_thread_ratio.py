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
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_varnish_worker_thread_ratio():
    return Dictionary(
        elements=[
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Percentage(title=_("Warning if below"), default_value=70.0),
                        Percentage(title=_("Critical if below"), default_value=60.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="varnish_worker_thread_ratio",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_varnish_worker_thread_ratio,
        title=lambda: _("Varnish Worker Thread Ratio"),
    )
)
