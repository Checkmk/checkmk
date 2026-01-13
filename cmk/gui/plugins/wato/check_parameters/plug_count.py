#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, Tuple


def _migrate_plug_count(params: tuple[int, int, int, int] | dict[str, object]) -> dict[str, object]:
    if isinstance(params, dict):
        return params
    cl, wl, wu, cu = params
    return {"levels_lower": (wl, cl), "levels_upper": (wu, cu)}


def _parameter_valuespec_plug_count() -> Migrate[dict[str, Any]]:
    return Migrate(
        valuespec=Dictionary(
            help=_("Levels for the number of active plugs in a device."),
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        title=_("Lower levels"),
                        elements=[
                            Integer(title=_("Warning if below or equal"), default_value=32),
                            Integer(title=_("Critical if below or equal"), default_value=30),
                        ],
                    ),
                ),
                (
                    "levels_upper",
                    Tuple(
                        title=_("Upper levels"),
                        elements=[
                            Integer(title=_("Warning at"), default_value=38),
                            Integer(title=_("Critical at"), default_value=40),
                        ],
                    ),
                ),
            ],
        ),
        migrate=_migrate_plug_count,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="plug_count",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_plug_count,
        title=lambda: _("Number of active Plugs"),
    )
)
