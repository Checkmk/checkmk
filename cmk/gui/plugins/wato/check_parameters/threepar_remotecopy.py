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
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_threepar_remotecopy():
    return Dictionary(
        elements=[
            (
                "1",
                MonitoringState(
                    title=_("Status: NORMAL"),
                    default_value=0,
                ),
            ),
            (
                "2",
                MonitoringState(
                    title=_("Status: STARTUP"),
                    default_value=1,
                ),
            ),
            (
                "3",
                MonitoringState(
                    title=_("Status: SHUTDOWN"),
                    default_value=1,
                ),
            ),
            (
                "4",
                MonitoringState(
                    title=_("Status: ENABLE"),
                    default_value=0,
                ),
            ),
            (
                "5",
                MonitoringState(
                    title=_("Status: DISBALE"),
                    default_value=2,
                ),
            ),
            (
                "6",
                MonitoringState(
                    title=_("Status: INVALID"),
                    default_value=2,
                ),
            ),
            (
                "7",
                MonitoringState(
                    title=_("Status: NODEUP"),
                    default_value=1,
                ),
            ),
            (
                "8",
                MonitoringState(
                    title=_("Status: UPGRADE"),
                    default_value=0,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="threepar_remotecopy",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threepar_remotecopy,
        title=lambda: _("3PAR Remote Copy"),
    )
)
