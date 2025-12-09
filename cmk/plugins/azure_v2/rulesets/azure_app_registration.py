#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

THIRTY_DAYS = 30 * 24 * 60 * 60
SEVEN_DAYS = 7 * 24 * 60 * 60


def _make_form() -> Dictionary:
    return Dictionary(
        elements={
            "expiration_time_secrets": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Time until secret credentials expiration"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((THIRTY_DAYS, SEVEN_DAYS)),
                )
            ),
            "expiration_time_certificates": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Time until certificate credentials expiration"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((THIRTY_DAYS, SEVEN_DAYS)),
                )
            ),
        }
    )


rule_spec_azure_app_registration = CheckParameters(
    name="azure_v2_app_registration",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    title=Title("Azure App Registration"),
    condition=HostAndItemCondition(item_title=Title("Credentials")),
)
