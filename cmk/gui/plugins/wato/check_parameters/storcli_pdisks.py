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


def _item_spec_storcli_pdisks():
    return TextInput(
        title=_("PDisk EID:Slot-Device"),
        allow_empty=False,
    )


def _parameter_valuespec_storcli_pdisks():
    return Dictionary(
        title=_("Evaluation of PDisk States"),
        elements=[
            (
                "Dedicated Hot Spare",
                MonitoringState(
                    title=_("State for <i>Dedicated Hot Spare</i>"),
                    default_value=0,
                ),
            ),
            (
                "Global Hot Spare",
                MonitoringState(
                    title=_("State for <i>Global Hot Spare</i>"),
                    default_value=0,
                ),
            ),
            (
                "Unconfigured Good",
                MonitoringState(
                    title=_("State for <i>Unconfigured Good</i>"),
                    default_value=0,
                ),
            ),
            (
                "Unconfigured Bad",
                MonitoringState(
                    title=_("State for <i>Unconfigured Bad</i>"),
                    default_value=1,
                ),
            ),
            (
                "Online",
                MonitoringState(
                    title=_("State for <i>Online</i>"),
                    default_value=0,
                ),
            ),
            (
                "Offline",
                MonitoringState(
                    title=_("State for <i>Offline</i>"),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storcli_pdisks",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_storcli_pdisks,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storcli_pdisks,
        title=lambda: _("LSI RAID physical disks"),
    )
)
