#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_proxmox_ve_snapshot_age_requirements():
    return Dictionary(
        elements=[
            (
                "oldest_levels",
                Tuple(
                    title=_("Max age of the oldest snapshot"),
                    elements=[
                        Age(
                            title=_("Warning at"),
                            display=["days", "hours"],
                            default_value=int(60 * 60 * 24 * 1),
                        ),
                        Age(
                            title=_("Critical at"),
                            display=["days", "hours"],
                            default_value=int(60 * 60 * 24 * 2),
                        ),
                    ],
                ),
            )
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Proxmox VE VM Snapshot Age"),
        check_group_name="proxmox_ve_vm_snapshot_age",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_proxmox_ve_snapshot_age_requirements,
    )
)
