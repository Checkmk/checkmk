#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Percentage, TextInput, Tuple


def _parameter_valuespec_db2_mem():
    return Tuple(
        elements=[
            Percentage(title=_("Warning if less than"), unit=_("% memory left")),
            Percentage(title=_("Critical if less than"), unit=_("% memory left")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_mem",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Instance name"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_db2_mem,
        title=lambda: _("DB2 memory usage"),
    )
)
