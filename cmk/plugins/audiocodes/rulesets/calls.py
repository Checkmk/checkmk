#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_audiocores_calls() -> Dictionary:
    return Dictionary(
        elements={
            "asr_lower_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for average success ratio"),
                    form_spec_template=Percentage(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((80.0, 70.0)),
                ),
            )
        }
    )


rule_spec_audiocodes_calls = CheckParameters(
    name="audiocodes_calls",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_audiocores_calls,
    title=Title("AudioCodes SBC Calls"),
    condition=HostCondition(),
)
