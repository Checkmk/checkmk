#!/usr/bin/env python3
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


def _parameter_valuespec_k8s_roles():
    return Dictionary(
        elements=[
            (
                "total",
                Tuple(
                    title=_("Total"),
                    elements=[
                        Integer(title=_("Warning above"), default_value=80),
                        Integer(title=_("Critical above"), default_value=90),
                    ],
                ),
            ),
            (
                "cluster_roles",
                Tuple(
                    title=_("Cluster roles"),
                    elements=[
                        Integer(title=_("Warning above"), default_value=80),
                        Integer(title=_("Critical above"), default_value=90),
                    ],
                ),
            ),
            (
                "roles",
                Tuple(
                    title=_("Roles"),
                    elements=[
                        Integer(title=_("Warning above"), default_value=80),
                        Integer(title=_("Critical above"), default_value=90),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_roles",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_roles,
        title=lambda: _("Kubernetes roles"),
        is_deprecated=True,
    )
)
