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
from cmk.gui.valuespec import Checkbox, Dictionary


def _parameter_valuespec_prism_alerts():
    return Dictionary(
        elements=[
            (
                "prism_central_only",
                Checkbox(
                    title=_("Consider alerts for Prism Central only"),
                    label=_("Activate (off: consider all alerts)"),
                    default_value=True,
                ),
            ),
        ],
        required_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_alerts",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_alerts,
        title=lambda: _("Nutanix Prism Alerts"),
    )
)
