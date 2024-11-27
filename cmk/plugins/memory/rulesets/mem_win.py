#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generic, NotRequired, TypedDict, TypeVar

from cmk.rulesets.v1 import Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    LevelDirection,
    Levels,
    LevelsConfigModel,
    migrate_to_lower_integer_levels,
    migrate_to_upper_integer_levels,
    Percentage,
    PredictiveLevels,
    TimeMagnitude,
    TimeSpan,
    validators,
)

_NumberT = TypeVar("_NumberT", int, float)


class _DualLevels(TypedDict, Generic[_NumberT]):
    upper: LevelsConfigModel[_NumberT]
    lower: LevelsConfigModel[_NumberT]


class _LevelsModel(TypedDict):
    perc_used: NotRequired[_DualLevels[float]]
    abs_used: NotRequired[_DualLevels[int]]
    abs_free: NotRequired[_DualLevels[int]]


_DUAL_LEVELS_KEYS = {"perc_used", "abs_used", "abs_free"}


class _CurrentModel(TypedDict):
    average: NotRequired[float]
    memory: NotRequired[_LevelsModel]
    pagefile: NotRequired[_LevelsModel]


_MiB = 1024**2
_GiB = 1024**3


def migrate(p: object) -> _CurrentModel:
    if not isinstance(p, dict):
        raise ValueError(p)

    new = _CurrentModel()
    if (avg := p.get("average")) is not None:
        new["average"] = avg if isinstance(avg, float) else float(avg) * 60.0
    if mem := p.get("memory"):
        new["memory"] = mem if _is_migrated(mem) else _migrate_alternative(mem)
    if pgf := p.get("pagefile"):
        new["pagefile"] = pgf if _is_migrated(pgf) else _migrate_alternative(pgf)
    return new


def _is_migrated(p: object) -> bool:
    return isinstance(p, dict) and set(p) <= _DUAL_LEVELS_KEYS


def _migrate_alternative(p: object) -> _LevelsModel:
    match p:
        case (float(w), float(c)):
            return _LevelsModel(
                perc_used=_DualLevels(
                    lower=("no_levels", None),
                    upper=("fixed", (w, c)),
                ),
            )
        case (int(w), int(c)):
            return _LevelsModel(
                abs_free=_DualLevels(
                    lower=("fixed", (int(w * _MiB), int(c * _MiB))),
                    upper=("no_levels", None),
                ),
            )
        case dict():
            if set(p) == {"upper", "lower"}:
                return _LevelsModel(
                    abs_used=_DualLevels(
                        lower=migrate_to_lower_integer_levels(p),
                        upper=migrate_to_upper_integer_levels(p),
                    ),
                )
            scaled = scale_predictive(p, _GiB)
            return _LevelsModel(
                abs_used=_DualLevels(
                    upper=migrate_to_upper_integer_levels(scaled),
                    lower=migrate_to_lower_integer_levels(scaled),
                ),
            )
        case other:
            raise ValueError(other)


def scale_predictive(p: dict, factor: float) -> dict:
    return {k: _scale_predictive_element(k, v, factor) for k, v in p.items()}


def _scale_predictive_element(k: str, v: object, factor: float) -> object:
    match k, v:
        case "levels_upper" | "levels_lower", (type_, (float(warn), float(crit))):
            return (type_, (warn * factor, crit * factor) if type_ == "absolute" else (warn, crit))
        case "levels_upper_min", (float(warn), float(crit)):
            return warn * factor, crit * factor
    return v


def _perc_used_levels(title: Title, metric: str) -> Dictionary:
    return Dictionary(
        title=title,
        elements={
            "lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Lower levels"),
                    form_spec_template=Percentage(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((20.0, 10.0)),
                    predictive=PredictiveLevels(
                        reference_metric=metric,
                        prefill_abs_diff=DefaultValue((10.0, 20.0)),
                    ),
                ),
                required=True,
            ),
            "upper": DictElement(
                parameter_form=Levels[float](
                    title=Title("Upper levels"),
                    form_spec_template=Percentage(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    predictive=PredictiveLevels(
                        reference_metric=metric,
                        prefill_abs_diff=DefaultValue((10.0, 20.0)),
                    ),
                ),
                required=True,
            ),
        },
    )


def _abs_levels(title: Title, metric: str) -> Dictionary:
    return Dictionary(
        title=title,
        elements={
            "lower": DictElement(
                parameter_form=Levels[int](
                    title=Title("Lower levels"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.GIBI],
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((2 * _GiB, _GiB)),
                    predictive=PredictiveLevels(
                        reference_metric=metric,
                        prefill_abs_diff=DefaultValue((_GiB, 2 * _GiB)),
                    ),
                ),
                required=True,
            ),
            "upper": DictElement(
                parameter_form=Levels[int](
                    title=Title("Upper levels"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.GIBI],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    predictive=PredictiveLevels(
                        reference_metric=metric,
                        prefill_abs_diff=DefaultValue((_GiB, 2 * _GiB)),
                    ),
                ),
                required=True,
            ),
        },
    )


def _parameters_memory_pagefile_win() -> Dictionary:
    return Dictionary(
        migrate=migrate,
        elements={
            "memory": DictElement(
                parameter_form=Dictionary(
                    title=Title("Memory levels"),
                    elements={
                        "perc_used": DictElement(
                            parameter_form=_perc_used_levels(
                                Title("Memory usage in percent"), "mem_used_percent"
                            ),
                        ),
                        "abs_used": DictElement(
                            parameter_form=_abs_levels(Title("Absolute used memory"), "mem_used"),
                        ),
                        "abs_free": DictElement(
                            parameter_form=_abs_levels(Title("Absolute free memory"), "mem_free"),
                        ),
                    },
                )
            ),
            "pagefile": DictElement(
                parameter_form=Dictionary(
                    title=Title("Commit charge levels"),
                    elements={
                        "perc_used": DictElement(
                            parameter_form=_perc_used_levels(
                                Title("Commit charge in percent (relative to commit limit)"),
                                "pagefile_used_percent",
                            ),
                        ),
                        "abs_used": DictElement(
                            parameter_form=_abs_levels(
                                Title("Absolute used commit charge"), "pagefile_used"
                            ),
                        ),
                        "abs_free": DictElement(
                            parameter_form=_abs_levels(
                                Title("Absolute commitable memory"), "pagefile_free"
                            ),
                        ),
                    },
                )
            ),
            "average": DictElement[float](
                parameter_form=TimeSpan(
                    title=Title("Averaging"),
                    displayed_magnitudes=[
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.SECOND,
                    ],
                    help_text=Help(
                        "If this parameter is set, all measured values will be averaged "
                        "over the specified time interval before levels are being applied. "
                        "By default, averaging is turned off. "
                    ),
                    custom_validate=(validators.NumberInRange(60.0, None),),
                    prefill=DefaultValue(3600.0),
                )
            ),
        },
    )


rule_spec_mem_win = rule_specs.CheckParameters(
    title=Title("Memory levels for Windows"),
    name="memory_pagefile_win",
    topic=rule_specs.Topic.OPERATING_SYSTEM,
    parameter_form=_parameters_memory_pagefile_win,
    condition=rule_specs.HostCondition(),
)
