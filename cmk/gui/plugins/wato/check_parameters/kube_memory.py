#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.memory_linux import UpperMemoryLevels
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_memory():
    return Dictionary(
        help=_(
            "Here you can configure absolute levels or percentual levels for memory request "
            "utilization and memory limit utilization, respectively."
        ),
        title=_("Memory"),
        elements=[
            (
                "request",
                UpperMemoryLevels(
                    _("request utilization"),
                    default_levels_type="ignore",
                    default_percents=(80.0, 90.0),
                ),
            ),
            (
                "limit",
                UpperMemoryLevels(
                    _("limit utilization"),
                    default_levels_type="perc_used",
                    default_percents=(80.0, 90.0),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_memory",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_memory,
        title=lambda: _("Kubernetes memory resource utilization"),
    )
)
