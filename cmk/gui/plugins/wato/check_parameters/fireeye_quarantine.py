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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_fireeye_quarantine():
    return Dictionary(
        elements=[
            (
                "usage",
                Tuple(
                    title=_("Levels for Quarantine Usage"),
                    elements=[
                        Integer(title="Warning at", default_value=70, unit="%"),
                        Integer(title="Critical at", default_value=80, unit="%"),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fireeye_quarantine",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fireeye_quarantine,
        title=lambda: _("Fireeye Quarantine Usage"),
    )
)
