#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, Tuple


def _migrate_quadruple(
    p: Mapping[str, tuple] | tuple[float, float, float, float],
) -> Mapping[str, tuple]:
    if isinstance(p, dict):
        return p
    cl, wl, cu, wu = p
    return {"levels_lower": (wl, cl), "levels": (wu, cu)}


def _parameter_valuespec_single_humidity():
    return Migrate(
        valuespec=Dictionary(
            help=_("This ruleset sets the threshold limits for humidity sensors"),
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        title=_("Lower levels"),
                        elements=[
                            Integer(title=_("Warning at or below"), unit="%"),
                            Integer(title=_("Critical at or below"), unit="%"),
                        ],
                    ),
                ),
                (
                    "levels",
                    Tuple(
                        title=_("Upper levels"),
                        elements=[
                            Integer(title=_("Warning at or above"), unit="%"),
                            Integer(title=_("Critical at or above"), unit="%"),
                        ],
                    ),
                ),
            ],
        ),
        migrate=_migrate_quadruple,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="single_humidity",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_single_humidity,
        title=lambda: _("Humidity levels for devices with a single sensor"),
    )
)
