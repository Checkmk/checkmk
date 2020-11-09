#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Alternative,
    Tuple,
    Age,
    FixedValue,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_vm_backup_requirements():
    # use Dictionary as Optional returning an empty dict if empty
    return Dictionary(elements=[(
        "age_levels_upper",
        Alternative(
            title=_("Backup conditions"),
            elements=[
                Tuple(
                    title=_("Set conditions"),
                    elements=[
                        Age(
                            title=_("Warning at"),
                            display=["days", "hours", "minutes"],
                            # bit more than a day
                            default_value=int(60 * 60 * 26),
                        ),
                        Age(
                            title=_("Critical at"),
                            display=["days", "hours", "minutes"],
                            # bit more than two days
                            default_value=int(60 * 60 * 50),
                        ),
                    ],
                ),
                FixedValue(None, title=_("No Conditions"), totext=""),
            ]))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Proxmox VM Backup"),
        check_group_name="proxmox_vm_backup_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vm_backup_requirements,
    ))
