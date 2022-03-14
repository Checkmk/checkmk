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


def __levels_upper(title):
    return wrap_with_no_levels_dropdown(
        title=title,
        value_spec=Tuple(
            elements=[
                Integer(title=_("Warning above")),
                Integer(title=_("Critical above")),
            ],
        ),
    )


def __levels_lower(title):
    return wrap_with_no_levels_dropdown(
        title=title,
        value_spec=Tuple(
            elements=[
                Integer(title=_("Warning below")),
                Integer(title=_("Critical below")),
            ],
        ),
    )


def _parameter_valuespec():
    return Dictionary(
        help=_(
            "Allows to define absolute levels for running, waiting, terminated and total containers."
        ),
        elements=[
            (
                "running_upper",
                __levels_upper(_("Define upper levels for number of running containers")),
            ),
            (
                "running_lower",
                __levels_lower(_("Define lower levels for number of running containers")),
            ),
            (
                "waiting_upper",
                __levels_upper(_("Define upper levels for number of waiting containers")),
            ),
            (
                "waiting_lower",
                __levels_lower(_("Define lower levels for number of waiting containers")),
            ),
            (
                "terminated_upper",
                __levels_upper(_("Define upper levels for number of terminated containers")),
            ),
            (
                "terminated_lower",
                __levels_lower(_("Define lower levels for number of terminated containers")),
            ),
            (
                "total_upper",
                __levels_upper(_("Define upper levels for number of total containers")),
            ),
            (
                "total_lower",
                __levels_lower(_("Define lower levels for number of total containers")),
            ),
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
