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


def _parameter_valuespec_plug_count():
    return Tuple(
        help=_("Levels for the number of active plugs in a device."),
        elements=[
            Integer(title=_("critical if below or equal"), default_value=30),
            Integer(title=_("warning if below or equal"), default_value=32),
            Integer(title=_("warning if above or equal"), default_value=38),
            Integer(title=_("critical if above or equal"), default_value=40),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="plug_count",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_plug_count,
        title=lambda: _("Number of active Plugs"),
    )
)
