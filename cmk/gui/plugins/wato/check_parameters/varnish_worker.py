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


def _parameter_valuespec_varnish_worker():
    return Dictionary(
        elements=[
            (
                "wrk_drop",
                Tuple(
                    title=_('Upper levels for "dropped work requests" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "wrk_failed",
                Tuple(
                    title=_('Upper levels for "worker threads not created" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "wrk_queued",
                Tuple(
                    title=_('Upper levels for "queued work requests" per second'),
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
        check_group_name="varnish_worker",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_varnish_worker,
        title=lambda: _("Varnish Worker"),
    )
)
