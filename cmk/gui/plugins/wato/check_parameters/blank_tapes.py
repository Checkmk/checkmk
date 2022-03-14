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


def _parameter_valuespec_blank_tapes():
    return Tuple(
        elements=[
            Integer(title=_("Warning below"), default_value=5),
            Integer(title=_("Critical below"), default_value=1),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="blank_tapes",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_blank_tapes,
        title=lambda: _("DIVA CSM: remaining blank tapes"),
    )
)
