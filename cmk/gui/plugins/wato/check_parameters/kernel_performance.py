#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_kernel_performance():
    return Dictionary(
        elements=[
            (
                "ctxt",
                Levels(
                    unit=_("events per second"),
                    title=_("Context Switches"),
                    default_levels=(1000, 5000),
                    default_difference=(500.0, 1000.0),
                    default_value=None,
                ),
            ),
            (
                "processes",
                Levels(
                    unit=_("events per second"),
                    title=_("Process Creations"),
                    default_levels=(1000, 5000),
                    default_difference=(500.0, 1000.0),
                    default_value=None,
                ),
            ),
            (
                "pgmajfault",
                Levels(
                    unit=_("events per second"),
                    title=_("Major Page Faults"),
                    default_levels=(1000, 5000),
                    default_difference=(500.0, 1000.0),
                    default_value=None,
                ),
            ),
            (
                "page_swap_in_levels_lower",
                Tuple(
                    title=_("Swap In Lower"),
                    elements=[
                        Float(title=_("Swap In warning below"), unit=_("events per second")),
                        Float(title=_("Swap In critical below"), unit=_("events per second")),
                    ],
                ),
            ),
            (
                "page_swap_in_levels",
                Tuple(
                    title=_("Swap In Upper"),
                    elements=[
                        Float(title=_("Swap In warning at"), unit=_("events per second")),
                        Float(title=_("Swap In critical at"), unit=_("events per second")),
                    ],
                ),
            ),
            (
                "page_swap_out_levels_lower",
                Tuple(
                    title=_("Swap Out Lower"),
                    elements=[
                        Float(title=_("Swap Out warning below"), unit=_("events per second")),
                        Float(title=_("Swap Out critical below"), unit=_("events per second")),
                    ],
                ),
            ),
            (
                "page_swap_out_levels",
                Tuple(
                    title=_("Swap Out Upper"),
                    elements=[
                        Float(title=_("Swap Out warning at"), unit=_("events per second")),
                        Float(title=_("Swap Out critical at"), unit=_("events per second")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kernel_performance",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_kernel_performance,
        title=lambda: _("Number of kernel events per second"),
    )
)
