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


def _parameter_valuespec_safenet_hsm_eventstats() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "critical_events",
                Tuple(
                    title=_("Critical events"),
                    help=_("Sets levels on total critical events since last counter reset."),
                    elements=[
                        Integer(title=_("Warning at"), default_value=0),
                        Integer(title=_("Critical at"), default_value=1),
                    ],
                ),
            ),
            (
                "noncritical_events",
                Tuple(
                    title=_("Noncritical events"),
                    help=_("Sets levels on total noncritical events since last counter reset."),
                    elements=[
                        Integer(title=_("Warning at"), default_value=0),
                        Integer(title=_("Critical at"), default_value=1),
                    ],
                ),
            ),
            (
                "critical_event_rate",
                Tuple(
                    title=_("Critical event rate"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.0001, unit=_("1/s")),
                        Float(title=_("Critical at"), default_value=0.0005, unit=_("1/s")),
                    ],
                ),
            ),
            (
                "noncritical_event_rate",
                Tuple(
                    title=_("Noncritical event rate"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.0001, unit=_("1/s")),
                        Float(title=_("Critical at"), default_value=0.0005, unit=_("1/s")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="safenet_hsm_eventstats",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_safenet_hsm_eventstats,
        title=lambda: _("Safenet HSM Event Stats"),
    )
)
