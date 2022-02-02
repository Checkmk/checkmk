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
from cmk.gui.valuespec import Dictionary, Integer, Tuple

######################################################################
# NOTE: This valuespec and associated check are deprecated and will be
#       removed in Checkmk version 2.2.
######################################################################


def _parameter_valuespec_k8s_nodes():
    return Dictionary(
        elements=[
            (
                "levels",
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


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_nodes",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_nodes,
        title=lambda: _("Kubernetes nodes"),
        is_deprecated=True,
    )
)
