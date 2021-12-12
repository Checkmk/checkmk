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
from cmk.gui.valuespec import Age, Checkbox, Integer, Tuple


def _parameter_valuespec_windows_updates():
    return Tuple(
        title=_("Parameters for the Windows Update Check with WSUS"),
        help=_("Set the according numbers to 0 if you want to disable alerting."),
        elements=[
            Integer(title=_("Warning if at least this number of important updates are pending")),
            Integer(title=_("Critical if at least this number of important updates are pending")),
            Integer(title=_("Warning if at least this number of optional updates are pending")),
            Integer(title=_("Critical if at least this number of optional updates are pending")),
            Age(title=_("Warning if time until forced reboot is less then"), default_value=604800),
            Age(
                title=_("Critical if time time until forced reboot is less then"),
                default_value=172800,
            ),
            Checkbox(title=_("display all important updates verbosely"), default_value=True),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_updates",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_windows_updates,
        title=lambda: _("WSUS (Windows Updates)"),
    )
)
