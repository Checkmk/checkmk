#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_fortimail_disk_usage():
    return Dictionary(
        elements=[
            (
                "disk_usage",
                Tuple(
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
                    title=_("Levels for disk usage"),
                    help=("Set levels on the disk usage."),
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortimail_disk_usage",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_fortimail_disk_usage,
        title=lambda: _("Fortinet FortiMail disk usage"),
    )
)
