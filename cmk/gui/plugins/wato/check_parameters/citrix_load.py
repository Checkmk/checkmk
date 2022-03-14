#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Percentage, Transform, Tuple


def _parameter_valuespec_citrix_load():
    return Transform(
        valuespec=Tuple(
            title=_("Citrix Server load"),
            elements=[
                Percentage(title=_("Warning at"), default_value=85.0, unit="percent"),
                Percentage(title=_("Critical at"), default_value=95.0, unit="percent"),
            ],
        ),
        forth=lambda x: (x[0] / 100.0, x[1] / 100.0),
        back=lambda x: (int(x[0] * 100), int(x[1] * 100)),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="citrix_load",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_citrix_load,
        title=lambda: _("Load of Citrix Server"),
    )
)
