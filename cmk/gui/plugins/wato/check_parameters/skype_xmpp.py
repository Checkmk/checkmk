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


def _parameter_valuespec_skype_xmpp():
    return Dictionary(
        elements=[
            (
                "failed_outbound_streams",
                Dictionary(
                    title=_("XMPP Failed outbound stream establishes"),
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
                "failed_inbound_streams",
                Dictionary(
                    title=_("XMPP Failed inbound stream establishes"),
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
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="skype_xmpp",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_xmpp,
        title=lambda: _("Skype for Business XMPP"),
    )
)
