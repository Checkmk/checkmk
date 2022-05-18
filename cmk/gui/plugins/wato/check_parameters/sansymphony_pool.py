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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Transform, Tuple


def _transform_valuespec_sansymphony_pool(params):
    """Transform to Checkmk version 2.2"""
    if isinstance(params, tuple):
        return {
            "allocated_pools_percentage_upper": (float(params[0]), float(params[1])),
        }
    return params


def _parameter_valuespec_sansymphony_pool():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "allocated_pools_percentage_upper",
                    Tuple(
                        title=_("Allocated pools"),
                        help=_("Set upper thresholds for the percentage of allocated pools"),
                        elements=[
                            Percentage(
                                title=_("Warning at"),
                                default_value=80.0,
                            ),
                            Percentage(
                                title=_("Critical at"),
                                default_value=90.0,
                            ),
                        ],
                    ),
                ),
            ],
        ),
        forth=_transform_valuespec_sansymphony_pool,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sansymphony_pool",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the pool"),
        ),
        parameter_valuespec=_parameter_valuespec_sansymphony_pool,
        title=lambda: _("Sansymphony pool allocation"),
    )
)
