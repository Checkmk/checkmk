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


def _parameter_valuespec_statgrab_mem():
    return Alternative(
        elements=[
            Tuple(
                title=_("Specify levels in percentage of total RAM"),
                elements=[
                    Percentage(
                        title=_("Warning at a usage of"),
                        # xgettext: no-python-format
                        unit=_("% of RAM"),
                        maxvalue=None,
                    ),
                    Percentage(
                        title=_("Critical at a usage of"),
                        # xgettext: no-python-format
                        unit=_("% of RAM"),
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
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="statgrab_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        is_deprecated=True,
        parameter_valuespec=_parameter_valuespec_statgrab_mem,
        title=lambda: _("Statgrab Memory Usage"),
    )
)
