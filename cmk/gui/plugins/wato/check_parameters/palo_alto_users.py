#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Integer, Percentage, Tuple


def _parameter_valuespec_palo_alto_users() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                CascadingDropdown(
                    title=_("Levels for logged-in users"),
                    choices=[
                        (
                            "perc_user",
                            _("Percentual levels for logged-in users"),
                            Tuple(
                                elements=[
                                    Percentage(title=_("Warning above")),
                                    Percentage(title=_("Critical above")),
                                ],
                            ),
                        ),
                        (
                            "abs_user",
                            _("Absolute levels for logged-in users"),
                            Tuple(
                                elements=[
                                    Integer(title=_("Warning above")),
                                    Integer(title=_("Critical above")),
                                ],
                            ),
                        ),
                        ("ignore", _("Do not impose levels")),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="palo_alto_users_rule",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_palo_alto_users,
        title=lambda: _("Palo Alto Users"),
    )
)
