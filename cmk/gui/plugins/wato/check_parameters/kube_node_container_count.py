#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def __levels(title):
    return Dictionary(
        title=title,
        elements=[
            (
                "levels_upper",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Integer(title=_("Warning above")),
                        Integer(title=_("Critical above")),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
        ],
    )


def _parameter_valuespec():
    return Dictionary(
        help=_(
            "Allows to define absolute levels for running, waiting, terminated and total containers."
        ),
        elements=[
            ("running", __levels(_("Number of running containers"))),
            ("waiting", __levels(_("Number of waiting containers"))),
            ("terminated", __levels(_("Number of terminated containers"))),
            ("total", __levels(_("Number of total containers"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_container_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes node containers"),
    )
)
