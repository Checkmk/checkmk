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
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis memory monitoring"
        ),
        elements={
            "memory_util": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Memory utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint((70.0, 80.0)),
                ),
            ),
            "evicted_keys": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Evicted keys"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_memory = CheckParameters(
    name="azure_v2_redis_memory",
    title=Title("Azure Redis memory"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
