#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _item_spec_storcli_vdrives():
    return TextInput(
        title=_("Virtual Drive"),
        allow_empty=False,
    )


def _parameter_valuespec_storcli_vdrives():
    return Dictionary(
        title=_("Evaluation of VDrive States"),
        elements=[
            (
                "Optimal",
                MonitoringState(
                    title=_("State for <i>Optimal</i>"),
                    default_value=0,
                ),
            ),
            (
                "Partially Degraded",
                MonitoringState(
                    title=_("State for <i>Partially Degraded</i>"),
                    default_value=1,
                ),
            ),
            (
                "Degraded",
                MonitoringState(
                    title=_("State for <i>Degraded</i>"),
                    default_value=2,
                ),
            ),
            (
                "Offline",
                MonitoringState(
                    title=_("State for <i>Offline</i>"),
                    default_value=1,
                ),
            ),
            (
                "Recovery",
                MonitoringState(
                    title=_("State for <i>Recovery</i>"),
                    default_value=1,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storcli_vdrives",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_storcli_vdrives,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storcli_vdrives,
        title=lambda: _("LSI RAID logical disks"),
    )
)
