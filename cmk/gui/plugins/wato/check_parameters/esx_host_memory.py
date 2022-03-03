#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Integer, ListOf, Percentage, Transform, Tuple


def _transform_memory_usage_params(params):
    # Introduced in v2.1.0i1
    if isinstance(params, tuple):
        return {"levels_upper": params}
    return params


def _esx_host_memory_elements():
    return [
        (
            "levels_upper",
            Tuple(
                title=_("Specify levels in percentage of total RAM"),
                elements=[
                    Percentage(title=_("Warning at a RAM usage of"), default_value=80.0),
                    Percentage(title=_("Critical at a RAM usage of"), default_value=90.0),
                ],
            ),
        ),
    ]


def _parameter_valuespec_esx_host_memory():
    return Transform(
        Dictionary(
            elements=_esx_host_memory_elements()
            + [
                (
                    "cluster",
                    ListOf(
                        valuespec=Tuple(
                            orientation="horizontal",
                            elements=[
                                Integer(
                                    title=_("Nodes"),
                                    help=_(
                                        "Apply these levels to clusters that have at least the following number of nodes:"
                                    ),
                                    minvalue=1,
                                ),
                                Dictionary(elements=_esx_host_memory_elements()),
                            ],
                        ),
                        title=_("Clusters: node specific memory utilization"),
                        help=_(
                            "Configure thresholds that apply to clusters based on how many nodes "
                            "they have."
                        ),
                    ),
                ),
            ],
        ),
        forth=_transform_memory_usage_params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_host_memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_esx_host_memory,
        title=lambda: _("Main memory usage of ESX host system"),
    )
)
