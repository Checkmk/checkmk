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


def _parameter_valuespec_vm_guest_tools():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "guestToolsCurrent",
                MonitoringState(
                    title=_("VMware Tools is installed, and the version is current"),
                    default_value=0,
                ),
            ),
            (
                "guestToolsNeedUpgrade",
                MonitoringState(
                    title=_("VMware Tools is installed, but the version is not current"),
                    default_value=1,
                ),
            ),
            (
                "guestToolsNotInstalled",
                MonitoringState(
                    title=_("VMware Tools have never been installed"),
                    default_value=2,
                ),
            ),
            (
                "guestToolsUnmanaged",
                MonitoringState(
                    title=_("VMware Tools is installed, but it is not managed by VMWare"),
                    default_value=0,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="vm_guest_tools",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vm_guest_tools,
        title=lambda: _("Virtual machine (for example ESX) guest tools status"),
    )
)
