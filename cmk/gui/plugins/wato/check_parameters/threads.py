#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Integer, Percentage, Tuple, ValueSpec

ParamsTuple = tuple[float, float]  # absolute levels only  # version 1
ParamsDictValue = ParamsTuple
ParamsDict = Mapping[str, ParamsDictValue]  # absolute and relative levels  # version 2
ParamsDictOptionalValue = str | tuple[str, ParamsDictValue]
ParamsDictOptional = Mapping[str, ParamsDictOptionalValue]  # levels can be removed  # version 3


def _optional(title: str, valuespec: ValueSpec) -> CascadingDropdown:
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("No levels")),
            ("levels", _("Set levels"), valuespec),
        ],
    )


def _parameter_valuespec_threads() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                _optional(
                    _("Absolute levels"),
                    Tuple(
                        elements=[
                            Integer(title=_("Warning at"), unit=_("threads"), default_value=2000),
                            Integer(title=_("Critical at"), unit=_("threads"), default_value=4000),
                        ],
                    ),
                ),
            ),
            (
                "levels_percent",
                _optional(
                    _("Relative levels"),
                    Tuple(
                        elements=[
                            Percentage(title=_("Warning at"), default_value=80),
                            Percentage(title=_("Critical at"), default_value=90),
                        ],
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="threads",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threads,
        title=lambda: _("Number of threads"),
    )
)
