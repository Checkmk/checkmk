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


def _item_spec_jvm_requests():
    return TextInput(
        title=_("Name of the virtual machine"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _parameter_valuespec_jvm_requests() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Lower levels for incoming requests to a JVM application server"),
                        unit=_("requests/sec"),
                        default_levels=(-1, -1),
                        direction="lower",
                    ),
                ),
                (
                    "levels_upper",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Upper levels for incoming requests to a JVM application server"),
                        unit=_("requests/sec"),
                        default_levels=(800, 1000),
                        direction="upper",
                    ),
                ),
            ],
        ),
        migrate=lambda p: (
            p
            if isinstance(p, dict)
            else {"levels_lower": (p[1], p[0]), "levels_upper": (p[2], p[3])}
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_requests",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_requests,
        parameter_valuespec=_parameter_valuespec_jvm_requests,
        title=lambda: _("JVM request count"),
    )
)
