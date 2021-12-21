#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_hivemanager_ng_devices():
    return Dictionary(
        elements=[
            (
                "max_clients",
                Tuple(
                    title=_("Number of clients"),
                    help=_("Number of clients connected to a Device."),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("clients")),
                        Integer(title=_("Critical at"), unit=_("clients")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hivemanager_ng_devices",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Hostname of the Device")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hivemanager_ng_devices,
        title=lambda: _("HiveManager NG Devices"),
    )
)
