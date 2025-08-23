#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis connections monitoring"
        ),
        elements={
            "connected_clients": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Connected clients"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((200, 250)),
                ),
            ),
            "created_connections": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Connections created rate"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="/s"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_connections = CheckParameters(
    name="azure_redis_connections",
    title=Title("Azure Redis connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
