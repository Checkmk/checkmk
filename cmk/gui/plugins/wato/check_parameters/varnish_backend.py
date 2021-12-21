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


def _parameter_valuespec_varnish_backend():
    return Dictionary(
        elements=[
            (
                "busy",
                Tuple(
                    title=_('Upper levels for "backend connections busy/too many" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "fail",
                Tuple(
                    title=_('Upper levels for "backend connections failures" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "unhealthy",
                Tuple(
                    title=_(
                        'Upper levels for "backend connections unhealthy/not attempted" per second'
                    ),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="varnish_backend",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_varnish_backend,
        title=lambda: _("Varnish Backend"),
    )
)
