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
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _parameter_valuespec_fortigate_antivirus_ips(rate_name: str) -> Dictionary:
    return Dictionary(
        elements=[
            (
                "detections",
                Tuple(
                    title=_("Detection rate"),
                    help=_("Define levels on the %s detection rate.") % rate_name,
                    elements=[
                        Float(
                            title=_("Warning at"),
                            size=6,
                            unit=_("detections/s"),
                            default_value=100.00,
                        ),
                        Float(
                            title=_("Critical at"),
                            size=6,
                            unit=_("detections/s"),
                            default_value=300.00,
                        ),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_antivirus",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(
            title=_("Virtual domain index"),
        ),
        parameter_valuespec=lambda: _parameter_valuespec_fortigate_antivirus_ips(_("virus")),
        title=lambda: _("Fortinet FortiGate AntiVirus Detections"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_ips",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(
            title=_("Virtual domain index"),
        ),
        parameter_valuespec=lambda: _parameter_valuespec_fortigate_antivirus_ips(_("intrusion")),
        title=lambda: _("Fortinet FortiGate IPS Detections"),
    )
)
