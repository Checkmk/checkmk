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


def _parameter_valuespec_varnish_fetch():
    return Dictionary(
        elements=[
            (
                "1xx",
                Tuple(
                    title=_('Upper levels for "fetch no body (1xx)" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "204",
                Tuple(
                    title=_('Upper levels for "fetch no body (204)" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "304",
                Tuple(
                    title=_('Upper levels for "fetch no body (304)" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "bad",
                Tuple(
                    title=_('Upper levels for "fetch had bad headers" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "eof",
                Tuple(
                    title=_('Upper levels for "fetch EOF" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "failed",
                Tuple(
                    title=_('Upper levels for "fetch failed" per second'),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.0),
                        Float(title=_("Critical at"), default_value=2.0),
                    ],
                ),
            ),
            (
                "zero",
                Tuple(
                    title=_('Upper levels for "fetch zero length" per second'),
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
        check_group_name="varnish_fetch",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_varnish_fetch,
        title=lambda: _("Varnish Fetch"),
    )
)
