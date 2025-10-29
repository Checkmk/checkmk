#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from typing import Any

from cmk.gui.form_specs.generators.alternative_utils import enable_deprecated_alternative
from cmk.gui.form_specs.unstable import CascadingSingleChoiceExtended
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    FixedValue,
    Float,
    FormSpec,
    Integer,
    LevelDirection,
    Percentage,
    Prefill,
    TimeSpan,
)


def TupleLevels(
    elements: list[FormSpec[Any]], title: Title | None = None, help_text: Help | None = None
) -> Tuple:
    # This function acts as placeholder and indicates that the TupleLevels
    # should be converted to a SimpleLevels form spec.
    return Tuple(title=title, help_text=help_text, elements=elements)


def OptionalTupleLevels(
    form_spec_template: Integer | Float | Percentage | TimeSpan | DataSize,
    title: Title | None = None,
    help_text: Help | None = None,
    level_direction: LevelDirection = LevelDirection.UPPER,
    prefill_fixed_levels: Prefill[tuple[int, int] | tuple[float, float]] | None = None,
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    # This function acts as placeholder and indicates that the OptionalTupleLevels should be
    # converted to a SimpleLevels form spec.
    # It arguments are compatible with the form spec SimpleLevels.
    # This should simplify the migration to a real SimpleLevels form spec in the future.

    if level_direction == LevelDirection.UPPER:
        title_warn = Title("Warning at")
        title_crit = Title("Critical at")
    else:
        title_warn = Title("Warning below")
        title_crit = Title("Critical below")

    elements: tuple[FormSpec[Any], FormSpec[Any]]
    if prefill_fixed_levels is None:
        elements = (
            dataclasses.replace(form_spec_template, title=title_warn),
            dataclasses.replace(form_spec_template, title=title_crit),
        )
    else:
        levels = prefill_fixed_levels.value
        warn, crit = levels
        if isinstance(form_spec_template, Float | Percentage | TimeSpan):
            assert isinstance(warn, float)
            assert isinstance(crit, float)
            elements = (
                dataclasses.replace(
                    form_spec_template, prefill=DefaultValue(warn), title=title_warn
                ),
                dataclasses.replace(
                    form_spec_template, prefill=DefaultValue(crit), title=title_crit
                ),
            )
        else:
            assert isinstance(warn, int)
            assert isinstance(crit, int)
            elements = (
                dataclasses.replace(
                    form_spec_template, prefill=DefaultValue(warn), title=title_warn
                ),
                dataclasses.replace(
                    form_spec_template, prefill=DefaultValue(crit), title=title_crit
                ),
            )

    return enable_deprecated_alternative(
        CascadingSingleChoiceExtended(
            title=title,
            elements=[
                CascadingSingleChoiceElementExtended(
                    name="no_levels",
                    title=Title("No Levels"),
                    parameter_form=FixedValue(
                        value=None,
                        label=Label("(Do not impose levels, always be OK)"),
                    ),
                ),
                CascadingSingleChoiceElementExtended(
                    name="use_levels",
                    title=Title("Fixed levels"),
                    parameter_form=Tuple(help_text=help_text, elements=elements),
                ),
            ],
            prefill=DefaultValue("no_levels"),
        ),
        match_function=lambda v: 0 if v is None else 1,
    )
