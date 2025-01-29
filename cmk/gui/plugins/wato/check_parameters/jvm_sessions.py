#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput


def _item_spec_jvm_sessions():
    return TextInput(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _migrate_quadruple(
    params: tuple[int, int, int, int] | dict[str, tuple[int, int]],
) -> dict[str, tuple[int, int]]:
    if isinstance(params, dict):
        return params
    wl, cl, wu, cu = params
    return {
        "levels_lower": (wl, cl),
        "levels_upper": (wu, cu),
    }


def _parameter_valuespec_jvm_sessions():
    return Migrate(
        valuespec=Dictionary(
            title=_(
                "Levels for the number of current connections to a JVM application on the servlet level"
            ),
            elements=[
                (
                    "levels_lower",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Lower levels"),
                    ),
                ),
                (
                    "levels_upper",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Upper levels"),
                        default_levels=(800, 1000),
                    ),
                ),
            ],
        ),
        migrate=_migrate_quadruple,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_sessions",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_sessions,
        parameter_valuespec=_parameter_valuespec_jvm_sessions,
        title=lambda: _("JVM session count"),
    )
)
