#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import wrap_with_no_levels_dropdown
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def __levels(key, title_upper, title_lower):
    return [
        (
            key + "_levels_upper",
            wrap_with_no_levels_dropdown(
                title_upper,
                Tuple(
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ),
        (
            key + "_levels_lower",
            wrap_with_no_levels_dropdown(
                title_lower,
                Tuple(
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
        ),
    ]


def _parameter_valuespec_kube_node_count():
    return Dictionary(
        elements=__levels(
            "worker",
            _("Maximum number of ready worker nodes"),
            _("Minimum number of ready worker nodes"),
        )
        + __levels(
            "control_plane",
            _("Maximum number of ready control plane nodes"),
            _("Minimum number of ready control plane nodes"),
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_kube_node_count,
        title=lambda: _("Kubernetes node count"),
    )
)
