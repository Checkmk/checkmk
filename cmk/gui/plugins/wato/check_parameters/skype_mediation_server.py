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


def _parameter_valuespec_skype_mediation_server():
    return Dictionary(
        elements=[
            (
                "load_call_failure_index",
                Dictionary(
                    title=_("Load Call Failure Index"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=10),
                                    Integer(title=_("Critical at"), default_value=20),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "failed_calls_because_of_proxy",
                Dictionary(
                    title=_("Failed calls caused by unexpected interaction from proxy"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=10),
                                    Integer(title=_("Critical at"), default_value=20),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "failed_calls_because_of_gateway",
                Dictionary(
                    title=_("Failed calls caused by unexpected interaction from gateway"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning at"), default_value=10),
                                    Integer(title=_("Critical at"), default_value=20),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "media_connectivity_failure",
                Dictionary(
                    title=_("Media Connectivity Check Failure"),
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
        check_group_name="skype_mediation_server",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_mediation_server,
        title=lambda: _("Skype for Business Mediation Server"),
    )
)
