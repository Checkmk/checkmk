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
from cmk.gui.valuespec import Integer, OptionalDropdownChoice, Tuple


def _parameter_valuespec_memory_relative():
    return OptionalDropdownChoice(
        title=_("Memory usage"),
        choices=[(None, _("Do not impose levels"))],
        otherlabel=_("Percentual levels ->"),
        explicit=Tuple(
            elements=[
                Integer(title=_("Warning at"), default_value=85, unit="%"),
                Integer(title=_("Critical at"), default_value=90, unit="%"),
            ],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_relative",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_memory_relative,
        title=lambda: _("Main memory usage for Brocade fibre channel switches"),
    )
)
