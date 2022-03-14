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
from cmk.gui.valuespec import Alternative, Integer, Percentage, Tuple


def _parameter_valuespec_general_flash_usage():
    return Alternative(
        elements=[
            Tuple(
                title=_("Specify levels in percentage of total Flash"),
                elements=[
                    Percentage(
                        title=_("Warning at a usage of"),
                        # xgettext: no-python-format
                        label=_("% of Flash"),
                        maxvalue=None,
                    ),
                    Percentage(
                        title=_("Critical at a usage of"),
                        # xgettext: no-python-format
                        label=_("% of Flash"),
                        maxvalue=None,
                    ),
                ],
            ),
            Tuple(
                title=_("Specify levels in absolute usage values"),
                elements=[
                    Integer(title=_("Warning at"), unit=_("MB")),
                    Integer(title=_("Critical at"), unit=_("MB")),
                ],
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="general_flash_usage",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_general_flash_usage,
        title=lambda: _("Flash Space Usage"),
    )
)
