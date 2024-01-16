#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    PredictiveLevels,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Filesize,
    Integer,
    Migrate,
    Percentage,
    Transform,
    Tuple,
)

_PercUsedModel = tuple[float, float]
_AbsFreeModel = tuple[int, int]
_PredictiveModel = dict

_MiB = 1024**2
_GiB = float(1024**3)


def _migrate(
    p: dict[
        str,
        int
        | _PercUsedModel
        | _AbsFreeModel
        | tuple[str, _PercUsedModel | _AbsFreeModel | _PredictiveModel],
    ]
) -> dict[str, int | tuple[str, _PercUsedModel | _AbsFreeModel | _PredictiveModel]]:
    """
    >>> from pprint import pprint
    >>> pprint(_migrate(
    ...     {
    ...         'average': 3,
    ...         'memory': (1, 2),
    ...         'pagefile': {'see': 'doctest below'},
    ...     }
    ... ))
    {'average': 3,
     'memory': ('abs_free', (1048576, 2097152)),
     'pagefile': ('predictive', {'see': 'doctest below'})}
    """
    return {
        k: v
        if isinstance(v, int) or (isinstance(v, tuple) and isinstance(v[0], str))
        else _migrate_alternative(v)
        for k, v in p.items()
    }


def _migrate_alternative(
    p: _PercUsedModel | _AbsFreeModel | _PredictiveModel,
) -> (
    tuple[Literal["perc_used"], tuple[float, float]]
    | tuple[Literal["abs_free"], tuple[int, int]]
    | tuple[Literal["predictive"], dict]
):
    if isinstance(p, tuple):
        w, c = p
        if isinstance(w, float):
            return ("perc_used", (float(w), float(c)))
        return ("abs_free", (int(w) * _MiB, int(c) * _MiB))
    return ("predictive", p)


def _scale_predictive(p: _PredictiveModel, factor: float) -> _PredictiveModel:
    """
    >>> from pprint import pprint
    >>> pprint(_scale_predictive(
    ...     {
    ...         '__get_predictive_levels__': None,
    ...         'period': 'minute',
    ...         'horizon': 4,
    ...         'levels_upper': ('absolute', (0.5, 1.0)),
    ...         'levels_lower': ('stdev', (2.0, 4.0)),
    ...     },
    ...     1024.0,
    ... ))
    {'__get_predictive_levels__': None,
     'horizon': 4,
     'levels_lower': ('stdev', (2.0, 4.0)),
     'levels_upper': ('absolute', (512.0, 1024.0)),
     'period': 'minute'}
    """
    return {k: _scale_predictive_element(k, v, factor) for k, v in p.items()}


def _scale_predictive_element(k: str, v: Any, factor: float) -> Any:
    match k:
        case "levels_upper" | "levels_lower":
            type_, (warn, crit) = v
            return (type_, (warn * factor, crit * factor) if type_ == "absolute" else (warn, crit))
        case "levels_upper_min":
            warn, crit = v
            return warn * factor, crit * factor
    return v


def _prec_used_levels() -> Tuple:
    return Tuple(
        elements=[
            Percentage(title=_("Warning at"), default_value=80.0),
            Percentage(title=_("Critical at"), default_value=90.0),
        ],
    )


def _abs_free_levels() -> Tuple:
    return Tuple(
        elements=[
            Filesize(title=_("Warning at or below")),
            Filesize(title=_("Critical at or below")),
        ],
    )


def _predictive_levels() -> Transform:
    return Transform(  # *not* transform until we migrate to new API and can use Datasize inside PredictiveLevels!
        PredictiveLevels(unit=_("GiB"), default_difference=(0.5, 1.0)),
        to_valuespec=lambda p: _scale_predictive(p, 1.0 / _GiB),
        from_valuespec=lambda p: _scale_predictive(p, _GiB),
    )


def _parameter_valuespec_memory_pagefile_win():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "memory",
                    CascadingDropdown(
                        title=_("Memory Levels"),
                        choices=[
                            ("perc_used", _("Memory usage in percent"), _prec_used_levels()),
                            ("abs_free", _("Absolute free memory"), _abs_free_levels()),
                            ("predictive", _("Predicteve levels for usage"), _predictive_levels()),
                        ],
                    ),
                ),
                (
                    "pagefile",
                    CascadingDropdown(
                        title=_("Commit charge Levels"),
                        choices=[
                            (
                                "perc_used",
                                _("Commit charge in percent (relative to commit limit)"),
                                _prec_used_levels(),
                            ),
                            ("abs_free", _("Absolute commitable memory"), _abs_free_levels()),
                            (
                                "predictive",
                                _("Predicteve levels for commit charge"),
                                _predictive_levels(),
                            ),
                        ],
                    ),
                ),
                (
                    "average",
                    Integer(
                        title=_("Averaging"),
                        help=_(
                            "If this parameter is set, all measured values will be averaged "
                            "over the specified time interval before levels are being applied. Per "
                            "default, averaging is turned off. "
                        ),
                        unit=_("minutes"),
                        minvalue=1,
                        default_value=60,
                    ),
                ),
            ],
        ),
        migrate=_migrate,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_pagefile_win",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_pagefile_win,
        title=lambda: _("Memory levels for Windows"),
    )
)
