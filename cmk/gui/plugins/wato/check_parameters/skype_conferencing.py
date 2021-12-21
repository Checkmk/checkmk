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
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_skype_conferencing():
    return Dictionary(
        elements=[
            (
                "incomplete_calls",
                Dictionary(
                    title=_("Incomplete Calls"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=20.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=40.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "create_conference_latency",
                Dictionary(
                    title=_("Create Conference Latency"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"), unit=_("seconds"), default_value=5.0
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("seconds"),
                                        default_value=10.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "allocation_latency",
                Dictionary(
                    title=_("Conference Allocation Latency"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"), unit=_("seconds"), default_value=5.0
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("seconds"),
                                        default_value=10.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="skype_conferencing",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_conferencing,
        title=lambda: _("Skype for Business Conferencing"),
    )
)
