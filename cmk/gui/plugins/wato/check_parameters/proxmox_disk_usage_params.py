#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Tuple,
    Percentage,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_disk_percentage_levels():
    return Dictionary(
        elements=[
            ("levels",
             Tuple(
                 title=_("Levels"),
                 elements=[
                     Percentage(
                         title=_("Warning at"),
                         default_value=80.0,
                     ),
                     Percentage(
                         title=_("Critical at"),
                         default_value=90.0,
                     ),
                 ],
             )),
        ],
        required_keys=['levels'],  # There is only one value, so its required
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="proxmox_disk_percentage_used",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_disk_percentage_levels,
        title=lambda: _("Proxmox disk percentage used"),
    ))
