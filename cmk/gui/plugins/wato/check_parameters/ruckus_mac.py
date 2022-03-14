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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_ruckus_mac():
    return Dictionary(
        elements=[
            (
                "inside",
                Dictionary(
                    title=_("Inside unique MACs"),
                    elements=[
                        (
                            "levels_upper",
                            Tuple(
                                title=_("Upper levels"),
                                elements=[
                                    Integer(title=_("Warning at")),
                                    Integer(title=_("Critical at")),
                                ],
                            ),
                        ),
                        (
                            "levels_lower",
                            Tuple(
                                title=_("Lower levels"),
                                elements=[
                                    Integer(title=_("Warning if below")),
                                    Integer(title=_("Critical if below")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            (
                "outside",
                Dictionary(
                    title=_("Outside unique MACs"),
                    elements=[
                        (
                            "levels_upper",
                            Tuple(
                                title=_("Upper levels"),
                                elements=[
                                    Integer(title=_("Warning at")),
                                    Integer(title=_("Critical at")),
                                ],
                            ),
                        ),
                        (
                            "levels_lower",
                            Tuple(
                                title=_("Lower levels"),
                                elements=[
                                    Integer(title=_("Warning if below")),
                                    Integer(title=_("Critical if below")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ruckus_mac",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ruckus_mac,
        title=lambda: _("Ruckus Spot Unique MAC addresses"),
    )
)
