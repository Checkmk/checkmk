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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_pf_used_states():
    return Dictionary(
        elements=[
            (
                "used",
                Tuple(
                    title=_("Limits for the number of used states"),
                    elements=[
                        Integer(title=_("warning at")),
                        Integer(title=_("critical at")),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pf_used_states",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pf_used_states,
        title=lambda: _("Number of used states of OpenBSD PF engine"),
    )
)
