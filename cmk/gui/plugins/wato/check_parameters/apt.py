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
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_apt():
    return Dictionary(
        elements=[
            (
                "normal",
                MonitoringState(
                    title=_("State when normal updates are pending"),
                    default_value=1,
                ),
            ),
            (
                "security",
                MonitoringState(
                    title=_("State when security updates are pending"),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="apt",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_apt,
        title=lambda: _("APT Updates"),
    )
)
