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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_skype_edgeauth():
    return Dictionary(
        elements=[
            (
                "bad_requests",
                Dictionary(
                    title=_("Bad Requests Received"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=20,
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=40,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="skype_edgeauth",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_edgeauth,
        title=lambda: _("Skype for Business Edge Auth"),
    )
)
