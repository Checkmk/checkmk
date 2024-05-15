#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, Integer, Migrate, Percentage, Tuple


def _parameter_valuespec_windows_multipath():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "active_paths",
                    Alternative(
                        help=_(
                            "This rules sets the expected number of active paths for a multipath LUN."
                        ),
                        title=_("Expected active paths"),
                        elements=[
                            Integer(title=_("Expected number of active paths")),
                            Tuple(
                                title=_("Expected percentage of active paths"),
                                elements=[
                                    Integer(title=_("Expected number of active paths")),
                                    Percentage(title=_("Warning if less then")),
                                    Percentage(title=_("Critical if less then")),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
            title=_("Windows Multipath Count"),
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"active_paths": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_multipath",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_windows_multipath,
        title=lambda: _("Windows Multipath Count"),
    )
)
