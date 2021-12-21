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


def _parameter_valuespec_k8s_node_count():
    return Dictionary(
        elements=[
            ("worker", __levels(_("Number of worker nodes"))),
            ("control_plane", __levels(_("Number of control plane nodes"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_node_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_node_count,
        title=lambda: _("Kubernetes node count"),
    )
)
