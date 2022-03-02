#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
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


def _parameter_valuespec():
    return Dictionary(
        help=_(
            "Here you can configure absolute levels for total "
            "restart count and restarts in the last hour."
        ),
        title=_("Upper levels for restarts"),
        elements=[
            (
                "restart_count",
                wrap_with_no_levels_dropdown(
                    title=_("Total restarts"),
                    value_spec=Tuple(
                        elements=[
                            Integer(title=_("Warning at"), unit="restarts"),
                            Integer(title=_("Critical at"), unit="restarts"),
                        ],
                    ),
                ),
            ),
            (
                "restart_rate",
                wrap_with_no_levels_dropdown(
                    title=_("Restart rate"),
                    value_spec=Tuple(
                        elements=[
                            Integer(title=_("Warning at"), unit="restarts in last hour"),
                            Integer(title=_("Critical at"), unit="restarts in last hour"),
                        ],
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_restarts",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes pod restarts"),
    )
)
