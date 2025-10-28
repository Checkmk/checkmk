#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.unstable.legacy_converter.generators import OptionalTupleLevels
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_spec_antivir_update_age() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=OptionalTupleLevels(
                    title=Title("Levels for time since last update"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        )
                    ),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            )
        }
    )


rule_spec_antivir_update_age = CheckParameters(
    name="antivir_update_age",
    title=Title("AntiVirus last update age"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_antivir_update_age,
    condition=HostCondition(),
)
