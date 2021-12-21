#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_disk_failures():
    return Tuple(
        title=_("Number of disk failures"),
        elements=[
            Integer(title="Warning at", default_value=1),
            Integer(title="Critical at", default_value=2),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="disk_failures",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_disk_failures,
        title=lambda: _("Number of disk failures"),
    )
)
