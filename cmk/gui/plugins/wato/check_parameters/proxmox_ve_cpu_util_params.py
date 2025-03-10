#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Float, Integer, Tuple


def _parameter_valuespec_proxmox_ve_cpu_util():
    return Dictionary(
        required_keys=["util"],
        elements=[
            (
                "util",
                Alternative(
                    title=_("CPU Utilization levels"),
                    elements=[
                        Tuple(
                            title=_("Set conditions"),
                            elements=[
                                Float(
                                    minvalue=0.0,
                                    maxvalue=100.0,
                                    unit="%",
                                    default_value=90.0,
                                    title=_("Warning at"),
                                ),
                                Float(
                                    minvalue=0.0,
                                    maxvalue=100.0,
                                    unit="%",
                                    default_value=95.0,
                                    title=_("Critical at"),
                                ),
                            ],
                        ),
                        FixedValue(value=None, title=_("No Conditions"), totext=""),
                    ],
                ),
            ),
            ("average", Integer(minvalue=1, unit="minutes", title=_("Average CPU Value over"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="proxmox_ve_cpu_util",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_proxmox_ve_cpu_util,
        title=lambda: _("Proxmox VE CPU Utilization"),
    )
)
