#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_sles_license():
    return Dictionary(
        elements={
            "status": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Status"),
                    help_text=Help("Status of the SLES license"),
                    elements=[
                        SingleChoiceElement(name="Registered", title=Title("Registered")),
                        SingleChoiceElement(name="Ignore", title=Title("Ignore")),
                    ],
                ),
            ),
            "subscription_status": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Subscription"),
                    help_text=Help("Status of the SLES subscription"),
                    elements=[
                        SingleChoiceElement(name="ACTIVE", title=Title("ACTIVE")),
                        SingleChoiceElement(name="Ignore", title=Title("Ignore")),
                    ],
                ),
            ),
            "days_left": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Time until license expiration"),
                    help_text=Help("Remaining days until the SLES license expires"),
                    level_direction=LevelDirection.LOWER,
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.DAY]),
                    prefill_fixed_levels=InputHint((14.0, 7.0)),
                ),
            ),
        }
    )


rule_spec_sles_license = CheckParameters(
    name="sles_license",
    title=Title("SLES License"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_rulespec_sles_license,
    condition=HostCondition(),
)
