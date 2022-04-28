#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing as t

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Integer,
    Percentage,
    Transform,
    Tuple,
    ValueSpec,
)

ParamsTuple = t.Tuple[float, float]  # absolute levels only  # version 1
ParamsDictValue = ParamsTuple
ParamsDict = t.Mapping[str, ParamsDictValue]  # absolute and relative levels  # version 2
ParamsDictOptionalValue = t.Union[str, t.Tuple[str, ParamsDictValue]]
ParamsDictOptional = t.Mapping[str, ParamsDictOptionalValue]  # levels can be removed  # version 3


def _has_current_format(value: t.Union[ParamsDictValue, ParamsDictOptionalValue]) -> bool:
    return value == "no_levels" or value[0] == "levels"


def _transform_forth(params):
    """
    # very old format
    >>> _transform_forth((20, 30))
    {'levels': ('levels', (20, 30))}

    # format that can handle relative and absolute levels
    >>> _transform_forth({"levels_percent": (20, 30)})
    {'levels_percent': ('levels', (20, 30))}

    # don't modify current format
    >>> _transform_forth({"levels_percent": ("levels", (20, 30)), "levels": "no_levels"})
    {'levels_percent': ('levels', (20, 30)), 'levels': 'no_levels'}

    """
    if not isinstance(params, dict):
        params = {"levels": params}
    if params and not _has_current_format(next(iter(params.values()))):
        return {key: ("levels", value) for key, value in params.items()}
    return params


def _optional(title: str, valuespec: ValueSpec) -> CascadingDropdown:
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("No levels")),
            ("levels", _("Set levels"), valuespec),
        ],
    )


def _parameter_valuespec_threads():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    _optional(
                        _("Absolute levels"),
                        Tuple(
                            elements=[
                                Integer(
                                    title=_("Warning at"), unit=_("threads"), default_value=2000
                                ),
                                Integer(
                                    title=_("Critical at"), unit=_("threads"), default_value=4000
                                ),
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
        ),
        forth=_transform_forth,
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
