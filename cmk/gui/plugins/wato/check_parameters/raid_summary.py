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
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_raid_summary():
    return Dictionary(
        elements=[
            (
                "use_device_states",
                DropdownChoice(
                    title=_("Use device states and overwrite expected status"),
                    choices=[
                        (False, _("Ignore")),
                        (True, _("Use device states")),
                    ],
                    default_value=True,
                ),
            ),
        ],
        ignored_keys=[
            "available",
            "broken",
            "notavailable",
            "notsupported",
            "present",
            "readying",
            "recovering",
            "partbroken",
            "spare",
            "formatting",
            "unformated",
            "notexist",
            "copying",
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="raid_summary",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_raid_summary,
        title=lambda: _("RAID: summary state"),
    )
)
