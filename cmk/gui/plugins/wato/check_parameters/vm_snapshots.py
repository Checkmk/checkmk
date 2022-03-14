#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_vm_snapshots():
    return Dictionary(
        elements=[
            (
                "age_oldest",
                Tuple(
                    title=_("Age of the oldest snapshot"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "age",
                Tuple(
                    title=_("Age of the latest snapshot"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="vm_snapshots",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vm_snapshots,
        title=lambda: _("Virtual Machine Snapshots"),
    )
)
