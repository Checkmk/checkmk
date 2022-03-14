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
from cmk.gui.valuespec import Percentage, Tuple


def _parameter_valuespec_juniper_mem():
    return Tuple(
        title=_("Specify levels in percentage of total memory usage"),
        elements=[
            Percentage(
                title=_("Warning at a usage of"),
                # xgettext: no-python-format
                unit=_("% of RAM"),
                default_value=80.0,
                maxvalue=100.0,
            ),
            Percentage(
                title=_("Critical at a usage of"),
                # xgettext: no-python-format
                unit=_("% of RAM"),
                default_value=90.0,
                maxvalue=100.0,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="juniper_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_juniper_mem,
        title=lambda: _("Juniper Memory Usage"),
    )
)
