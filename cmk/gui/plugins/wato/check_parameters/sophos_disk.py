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
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_sophos_disk():
    return Dictionary(
        elements=[
            (
                "disk_levels",
                Tuple(
                    title=_("Disk percentage usage"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=80),
                        Percentage(title=_("Critical at"), default_value=90),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sophos_disk",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sophos_disk,
        title=lambda: _("Sophos Disk utilization"),
    )
)
