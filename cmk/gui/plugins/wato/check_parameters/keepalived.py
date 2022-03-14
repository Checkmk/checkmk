#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_keepalived():
    return Dictionary(
        elements=[
            (
                "master",
                MonitoringState(
                    title=_("master"),
                    default_value=0,
                ),
            ),
            (
                "unknown",
                MonitoringState(
                    title=_("unknown"),
                    default_value=3,
                ),
            ),
            (
                "init",
                MonitoringState(
                    title=_("init"),
                    default_value=0,
                ),
            ),
            (
                "backup",
                MonitoringState(
                    title=_("backup"),
                    default_value=0,
                ),
            ),
            (
                "fault",
                MonitoringState(
                    title=_("fault"),
                    default_value=2,
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="keepalived",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("VRRP Instance"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_keepalived,
        title=lambda: _("Keepalived Parameters"),
    )
)
