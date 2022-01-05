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
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Integer, Tuple


def __optional(title, value_spec):
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("No Levels")),
            ("levels", _("Impose levels"), value_spec),
        ],
        default_value="no_levels",
    )


def __levels(key, title_upper, title_lower):
    return [
        (
            key + "_levels_upper",
            __optional(
                title_upper,
                Tuple(
                    elements=[
                        Integer(title=_("Warning above")),
                        Integer(title=_("Critical above")),
                    ],
                ),
            ),
        ),
        (
            key + "_levels_lower",
            __optional(
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
            _("Set upper levels of worker nodes"),
            _("Set lower levels of worker nodes"),
        )
        + __levels(
            "control_plane",
            _("Set upper levels of control plane nodes"),
            _("Set lower levels of control plane nodes"),
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
