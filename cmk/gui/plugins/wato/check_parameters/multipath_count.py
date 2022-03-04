#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    TextInput,
    Transform,
    Tuple,
)


def _parameter_valuespec_multipath_count():
    return Alternative(
        help=_(
            "This rules sets the expected number of active paths for a multipath LUN "
            "on ESX servers"
        ),
        title=_("Match type"),
        elements=[
            FixedValue(
                value=None,
                title=_("OK if standby count is zero or equals active paths."),
                totext="",
            ),
            Dictionary(
                title=_("Custom settings"),
                elements=[
                    (
                        element,
                        Transform(
                            valuespec=Tuple(
                                title=description,
                                elements=[
                                    Integer(title=_("Critical if less than")),
                                    Integer(title=_("Warning if less than")),
                                    Integer(title=_("Warning if more than")),
                                    Integer(title=_("Critical if more than")),
                                ],
                            ),
                            forth=lambda x: len(x) == 2
                            and (
                                0,
                                0,
                                x[0],
                                x[1],
                            )
                            or x,
                        ),
                    )
                    for (element, description) in [
                        ("active", _("Active paths")),
                        ("dead", _("Dead paths")),
                        ("disabled", _("Disabled paths")),
                        ("standby", _("Standby paths")),
                        ("unknown", _("Unknown paths")),
                    ]
                ],
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="multipath_count",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Path ID")),
        parameter_valuespec=_parameter_valuespec_multipath_count,
        title=lambda: _("ESX Multipath Count"),
    )
)
