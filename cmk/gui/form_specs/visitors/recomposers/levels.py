#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

import dataclasses
import enum
from collections.abc import Callable
from typing import Any, assert_never, Literal, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.gui.form_specs.unstable import OptionalChoice
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    FormSpec,
    InputHint,
    Integer,
    LevelDirection,
    Levels,
    LevelsType,
    Percentage,
    PredictiveLevels,
    Prefill,
    SimpleLevels,
    SimpleLevelsConfigModel,
    SingleChoice,
    SingleChoiceElement,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange

from .._type_defs import DefaultValue as FrontendDefaultValue

_NumberT = TypeVar("_NumberT", int, float)

_LevelsFormSpecModel = SimpleLevelsConfigModel[_NumberT] | tuple[Literal["predictive"], object]

_LevelsConfigModel = (
    SimpleLevelsConfigModel[_NumberT]
    | tuple[Literal["cmk_postprocessed"], Literal["predictive_levels"], object]
)


class _LevelDynamicChoice(enum.StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"
    PREDICTIVE = "predictive"


class _PredictiveLevelDefinition(enum.StrEnum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    STDEV = "stdev"


def _transform_from_disk(
    value: object,
) -> _LevelsFormSpecModel[_NumberT] | FrontendDefaultValue:
    if isinstance(value, FrontendDefaultValue):
        return value

    match value:
        case "no_levels", None:
            return "no_levels", None
        case "fixed", tuple(fixed_levels):
            return "fixed", fixed_levels
        case "predictive", {**predictive_levels}:  # format released in 2.3.0b3
            predictive_levels.pop("__reference_metric__", None)
            predictive_levels.pop("__direction__", None)
            return "predictive", predictive_levels
        case "cmk_postprocessed", "predictive_levels", {**predictive_levels}:
            predictive_levels.pop("__reference_metric__", None)
            predictive_levels.pop("__direction__", None)
            return "predictive", predictive_levels

    raise ValueError(value)


def _wrapped_transform_to_disk(
    form_spec: Levels[_NumberT] | SimpleLevels[_NumberT],
) -> Callable[[object], _LevelsConfigModel[_NumberT]]:
    def _transform_to_disk(
        value: object,
    ) -> _LevelsConfigModel[_NumberT]:
        match value:
            case "no_levels", None:
                return "no_levels", None
            case "fixed", tuple(fixed_levels):
                return "fixed", fixed_levels
            case "predictive", {**predictive_levels}:
                # The new prediction needs some more info that is hardcoded in the FormSpec
                # to do the prediction in the post-processing in cmk.base.checker
                assert isinstance(form_spec, Levels)
                return (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "__reference_metric__": form_spec.predictive.reference_metric,
                        "__direction__": form_spec.level_direction.value,
                        **predictive_levels,
                    },
                )

        raise ValueError(value)

    return _transform_to_disk


def _force_replace_prefill_and_title(
    form_spec_template: FormSpec[_NumberT],
    new_title: Title,
    new_prefill_value: _NumberT,
    new_prefill_type: (type[DefaultValue[_NumberT]] | type[InputHint[_NumberT]]),
) -> FormSpec[_NumberT]:
    # Currently all FormSpec[_NumberT] types have a prefill attribute,
    # but we don't know it statically. Let's just skip it in case
    # we someday invent one that does not have this attribute.
    if hasattr(form_spec_template, "prefill"):
        form_spec_template = dataclasses.replace(
            form_spec_template,
            prefill=new_prefill_type(new_prefill_value),  # type: ignore[call-arg]
        )
    return dataclasses.replace(form_spec_template, title=new_title)


def _get_prefill_type(
    prefill: Prefill[tuple[_NumberT, _NumberT]],
) -> type[DefaultValue[_NumberT]] | type[InputHint[_NumberT]]:
    return DefaultValue[_NumberT] if isinstance(prefill, DefaultValue) else InputHint[_NumberT]


def _fixed_levels(form_spec: Levels[_NumberT] | SimpleLevels[_NumberT]) -> Tuple:
    if form_spec.level_direction is LevelDirection.LOWER:
        warn_title = Title("Warning below")
        crit_title = Title("Critical below")
    else:
        warn_title = Title("Warning at")
        crit_title = Title("Critical at")

    prefill_type = _get_prefill_type(form_spec.prefill_fixed_levels)
    template = form_spec.form_spec_template
    match template:
        case Float() | TimeSpan() | Percentage():
            # mypy accepts int's in place of float's (https://github.com/python/mypy/issues/11385).
            # https://peps.python.org/pep-0484/#the-numeric-tower
            # However, int is not a subclass of float, issubclass(int, float) is false. In a
            # CascadingDropdown it is not acceptable to pass an int instead of a float (CMK-16402
            # shows the warning). We transform the value here, such that users which rely on mypy
            # validation are not disappointed.
            prefill_value = (
                float(form_spec.prefill_fixed_levels.value[0]),
                float(form_spec.prefill_fixed_levels.value[1]),
            )
        case Integer() | DataSize():
            prefill_value = form_spec.prefill_fixed_levels.value

        case _:
            raise MKGeneralException(f"Invalid number form spec for Levels: {template}")

    return Tuple(
        elements=[
            _force_replace_prefill_and_title(template, warn_title, prefill_value[0], prefill_type),
            _force_replace_prefill_and_title(template, crit_title, prefill_value[1], prefill_type),
        ],
        layout="vertical",
    )


def _no_levels() -> FixedValue[None]:
    return FixedValue(
        value=None, title=Title("No levels"), label=Label("Do not impose levels, always be OK")
    )


def _get_level_computation_dropdown(
    field_spec: FormSpec[_NumberT],
    predictive_levels: PredictiveLevels[_NumberT],
    level_direction: LevelDirection,
) -> CascadingSingleChoice:
    if level_direction is LevelDirection.UPPER:
        warn_title = Title("Warning above")
        crit_title = Title("Critical above")
    elif level_direction is LevelDirection.LOWER:
        warn_title = Title("Warning below")
        crit_title = Title("Critical below")
    else:
        assert_never(level_direction)

    abs_diff_prefill_type = _get_prefill_type(predictive_levels.prefill_abs_diff)
    rel_diff_prefill_type = _get_prefill_type(predictive_levels.prefill_rel_diff)
    stdev_diff_prefill_type = _get_prefill_type(predictive_levels.prefill_stdev_diff)

    return CascadingSingleChoice(
        title=Title("Level definition in relation to the predicted value"),
        elements=[
            CascadingSingleChoiceElement(
                name=_PredictiveLevelDefinition.ABSOLUTE.value,
                title=Title("Absolute difference"),
                parameter_form=Tuple(
                    help_text=Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a fixed absolute value"
                    ),
                    elements=[
                        _force_replace_prefill_and_title(
                            field_spec,
                            warn_title,
                            predictive_levels.prefill_abs_diff.value[0],
                            abs_diff_prefill_type,
                        ),
                        _force_replace_prefill_and_title(
                            field_spec,
                            crit_title,
                            predictive_levels.prefill_abs_diff.value[1],
                            abs_diff_prefill_type,
                        ),
                    ],
                ),
            ),
            CascadingSingleChoiceElement(
                name=_PredictiveLevelDefinition.RELATIVE.value,
                title=Title("Relative difference"),
                parameter_form=Tuple(
                    help_text=Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a percentage"
                    ),
                    elements=[
                        Percentage(
                            title=warn_title,
                            prefill=rel_diff_prefill_type(
                                predictive_levels.prefill_rel_diff.value[0]
                            ),
                        ),
                        Percentage(
                            title=crit_title,
                            prefill=rel_diff_prefill_type(
                                predictive_levels.prefill_rel_diff.value[1]
                            ),
                        ),
                    ],
                ),
            ),
            CascadingSingleChoiceElement(
                name=_PredictiveLevelDefinition.STDEV.value,
                title=Title("Standard deviation difference"),
                parameter_form=Tuple(
                    help_text=Help(
                        "The thresholds are calculated by increasing or decreasing the predicted "
                        "value by a multiple of the standard deviation"
                    ),
                    elements=[
                        Float(
                            title=warn_title,
                            unit_symbol=_("times the standard deviation"),
                            prefill=stdev_diff_prefill_type(
                                predictive_levels.prefill_stdev_diff.value[0]
                            ),
                        ),
                        Float(
                            title=crit_title,
                            unit_symbol=_("times the standard deviation"),
                            prefill=stdev_diff_prefill_type(
                                predictive_levels.prefill_stdev_diff.value[1]
                            ),
                        ),
                    ],
                ),
            ),
        ],
        prefill=DefaultValue(_PredictiveLevelDefinition.ABSOLUTE.value),
    )


def _predictive_bound(
    field_spec: FormSpec[_NumberT], level_direction: LevelDirection
) -> OptionalChoice:
    if level_direction is LevelDirection.UPPER:
        fixed_warn_title = Title("Warning level is at least")
        fixed_crit_title = Title("Critical level is at least")
        fixed_help_text = Help(
            "Regardless of how the dynamic levels are computed according to the prediction: they "
            "will never be set below the following limits. This avoids false alarms during times "
            "where the predicted levels would be very low."
        )

    elif level_direction is LevelDirection.LOWER:
        fixed_warn_title = Title("Warning level is at most")
        fixed_crit_title = Title("Critical level is at most")
        fixed_help_text = Help(
            "Regardless of how the dynamic levels are computed according to the prediction: they "
            "will never be set above the following limits. This avoids false alarms during times "
            "where the predicted levels would be very high."
        )
    else:
        assert_never(level_direction)

    return OptionalChoice(
        title=Title("Fixed limits"),
        label=Label("Set fixed limits"),
        parameter_form=Tuple(
            help_text=fixed_help_text,
            elements=[
                _force_replace_prefill_and_title(
                    field_spec,
                    fixed_warn_title,
                    0,
                    InputHint,
                ),
                _force_replace_prefill_and_title(
                    field_spec,
                    fixed_crit_title,
                    0,
                    InputHint,
                ),
            ],
        ),
    )


def _predictive_levels(
    predictive_levels: PredictiveLevels[_NumberT],
    field_spec: FormSpec[_NumberT],
    level_direction: LevelDirection,
) -> Dictionary:
    return Dictionary(
        title=Title("Predictive levels (only on CMC)"),
        elements={
            "period": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Base prediction on"),
                    help_text=Help(
                        "Define the periodicity in which the repetition of the measured data is "
                        "expected (monthly, weekly, daily or hourly)"
                    ),
                    elements=[
                        SingleChoiceElement(name="wday", title=Title("Day of the week")),
                        SingleChoiceElement(name="day", title=Title("Day of the month")),
                        SingleChoiceElement(name="hour", title=Title("Hour of the day")),
                        SingleChoiceElement(name="minute", title=Title("Minute of the hour")),
                    ],
                    prefill=DefaultValue("wday"),
                ),
            ),
            "horizon": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Length of historic data to consider"),
                    help_text=Help(
                        "How many days in the past Checkmk should evaluate the measurement data"
                    ),
                    unit_symbol=_("days"),
                    custom_validate=(NumberInRange(min_value=1),),
                    prefill=DefaultValue(90),
                ),
            ),
            "levels": DictElement(
                required=True,
                parameter_form=_get_level_computation_dropdown(
                    field_spec, predictive_levels, level_direction
                ),
            ),
            "bound": DictElement(
                required=True, parameter_form=_predictive_bound(field_spec, level_direction)
            ),
        },
    )


def recompose(form_spec: FormSpec[Any]) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, Levels | SimpleLevels):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a Levels/SimpleLevels form spec, got {type(form_spec)}"
        )

    elements: list[CascadingSingleChoiceElement[Any]] = [
        CascadingSingleChoiceElement(
            name=_LevelDynamicChoice.FIXED.value,
            title=Title("Fixed levels"),
            parameter_form=_fixed_levels(form_spec),
        ),
        CascadingSingleChoiceElement(
            name=_LevelDynamicChoice.NO_LEVELS.value,
            title=Title("No levels"),
            parameter_form=_no_levels(),
        ),
    ]

    if isinstance(form_spec, Levels):
        elements.append(
            CascadingSingleChoiceElement(
                name=_LevelDynamicChoice.PREDICTIVE.value,
                title=Title("Predictive levels (only on CMC)"),
                parameter_form=_predictive_levels(
                    form_spec.predictive,
                    form_spec.form_spec_template,
                    form_spec.level_direction,
                ),
            )
        )

    # Make typing happy
    assert isinstance(form_spec, Levels | SimpleLevels)

    prefill_ident = {
        LevelsType.NONE: _LevelDynamicChoice.NO_LEVELS.value,
        LevelsType.FIXED: _LevelDynamicChoice.FIXED.value,
        LevelsType.PREDICTIVE: _LevelDynamicChoice.PREDICTIVE.value,
    }[form_spec.prefill_levels_type.value]

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=CascadingSingleChoice(
            title=form_spec.title,
            help_text=form_spec.help_text,
            elements=elements,
            prefill=DefaultValue(prefill_ident),
        ),
        from_disk=_transform_from_disk,
        to_disk=_wrapped_transform_to_disk(form_spec),
        migrate=form_spec.migrate,
    )
