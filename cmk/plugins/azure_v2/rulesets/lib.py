# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    FixedValue,
    TimeMagnitude,
    TimeSpan,
)


def average_dict_element(also_has_extended_param: bool) -> DictElement[tuple[str, object]]:
    if also_has_extended_param:
        help = Help(
            "Average the instantaneous value over the specified number of minutes. "
            'Note: This does NOT affect "Levels over an extended period of time", which always '
            "checks the instantaneous value."
        )
    else:
        help = Help("Average the instantaneous value over the specified number of minutes.")

    return DictElement(
        required=False,
        parameter_form=CascadingSingleChoice(
            title=Title("Average metric value over a period of time"),
            elements=[
                CascadingSingleChoiceElement(
                    name="disable",
                    title=Title("Disable averaging"),
                    parameter_form=FixedValue(value=None),
                ),
                CascadingSingleChoiceElement(
                    name="seconds",
                    title=Title("Average over..."),
                    parameter_form=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.MINUTE],
                        help_text=help,
                    ),
                ),
            ],
        ),
    )
