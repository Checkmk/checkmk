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


def _parameter_valuespec_vm_heartbeat():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "heartbeat_missing",
                MonitoringState(
                    title=_("No heartbeat"),
                    help=_("Guest operating system may have stopped responding."),
                    default_value=2,
                ),
            ),
            (
                "heartbeat_intermittend",
                MonitoringState(
                    title=_("Intermittent heartbeat"),
                    help=_("May be due to high guest load."),
                    default_value=1,
                ),
            ),
            (
                "heartbeat_no_tools",
                MonitoringState(
                    title=_("Heartbeat tools missing or not installed"),
                    help=_("No VMWare Tools installed."),
                    default_value=1,
                ),
            ),
            (
                "heartbeat_ok",
                MonitoringState(
                    title=_("Heartbeat OK"),
                    help=_("Guest operating system is responding normally."),
                    default_value=0,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="vm_heartbeat",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vm_heartbeat,
        title=lambda: _("Virtual machine (for example ESX) heartbeat status"),
    )
)
