#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_ups_test():
    return Tuple(
        title=_("Time since last UPS selftest"),
        elements=[
            Integer(
                title=_("Warning Level for time since last self test"),
                help=_(
                    "Warning Level for time since last diagnostic test of the device. "
                    "For a value of 0 the warning level will not be used"
                ),
                unit=_("days"),
                default_value=0,
            ),
            Integer(
                title=_("Critical Level for time since last self test"),
                help=_(
                    "Critical Level for time since last diagnostic test of the device. "
                    "For a value of 0 the critical level will not be used"
                ),
                unit=_("days"),
                default_value=0,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ups_test",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_ups_test,
        title=lambda: _("Time since last UPS selftest"),
    )
)
