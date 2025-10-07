#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis Cache effectiveness "
            "monitoring"
        ),
        elements={
            "cache_hit_ratio": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Cache hit ratio"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint((80.0, 85.0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_cache_effectiveness = CheckParameters(
    name="azure_v2_redis_cache_effectiveness",
    title=Title("Azure Redis Cache effectiveness"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
