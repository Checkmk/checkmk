#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesNetworking,
)
from cmk.gui.valuespec import Integer, ListOf, Percentage, Tuple

# NOTE: The rulesets in this file were deprecated in version 2.1.0i1


def _parameter_valuespec_mem_cluster():
    return ListOf(
        valuespec=Tuple(
            elements=[
                Integer(title=_("Equal or more than"), unit=_("nodes")),
                Tuple(
                    title=_("Percentage of total RAM"),
                    elements=[
                        Percentage(title=_("Warning at a RAM usage of"), default_value=80.0),
                        Percentage(title=_("Critical at a RAM usage of"), default_value=90.0),
                    ],
                ),
            ]
        ),
        help=_("Here you can specify the total memory usage levels for clustered hosts."),
        title=_("Memory Usage"),
        add_label=_("Add limits"),
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="mem_cluster",
        group=RulespecGroupEnforcedServicesNetworking,
        parameter_valuespec=_parameter_valuespec_mem_cluster,
        title=lambda: _("Memory Usage of Clusters"),
        is_deprecated=True,
    )
)
