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


def _parameter_valuespec_sp_util():
    return Tuple(
        title=_("Specify levels in percentage of storage processor usage"),
        elements=[
            Percentage(title=_("Warning at"), default_value=50.0),
            Percentage(title=_("Critical at"), default_value=60.0),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sp_util",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_sp_util,
        title=lambda: _("Storage Processor Utilization"),
    )
)
