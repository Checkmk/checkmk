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
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def _parameter_valuespec_skype():
    return Dictionary(
        elements=[
            (
                "failed_search_requests",
                Dictionary(
                    title=_("Failed search requests"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=1.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=2.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "failed_locations_requests",
                Dictionary(
                    title=_("Failed Get Locations Requests"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=1.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=2.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "failed_file_requests",
                Dictionary(
                    title=_("Failed requests to Adressbook files"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=1.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=2.0,
                                    ),
                                ],
                            ),
                        )
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "join_failures",
                Dictionary(
                    title=_("Failures of the join launcher service"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=1),
                                    Integer(title=_("Critical at"), default_value=2),
                                ],
                            ),
                        )
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "failed_validate_cert",
                Dictionary(
                    title=_("Failed certificate validations"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=1),
                                    Integer(title=_("Critical at"), default_value=2),
                                ],
                            ),
                        )
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "timedout_ad_requests",
                Dictionary(
                    title=_("Timed out Active Directory Requests"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=0.01,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=0.02,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "5xx_responses",
                Dictionary(
                    title=_("HTTP 5xx Responses"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Float(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=1.0,
                                    ),
                                    Float(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=2.0,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "asp_requests_rejected",
                Dictionary(
                    title=_("ASP Requests Rejected"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=1),
                                    Integer(title=_("Critical at"), default_value=2),
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
        check_group_name="skype",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype,
        title=lambda: _("Skype for Business"),
    )
)
