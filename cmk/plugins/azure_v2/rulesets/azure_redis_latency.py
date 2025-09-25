#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis latency monitoring"
        ),
        elements={
            "serverside_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Server-side command latency"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
            "internode_upper": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Cache internode latency"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_latency = CheckParameters(
    name="azure_v2_redis_latency",
    title=Title("Azure Redis latency"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
