#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _packet_rate_levels(title: Title) -> DictElement[SimpleLevelsConfigModel[int]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Integer(
                label=Label("packets/s"),
                custom_validate=(validators.NumberInRange(0, None),),
            ),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue((100000, 200000)),
            migrate=migrate_to_integer_simple_levels,
        ),
    )


def _parameter_form_checkpoint_packets() -> Dictionary:
    return Dictionary(
        elements={
            "accepted": _packet_rate_levels(Title("Maximum rate of accepted packets")),
            "rejected": _packet_rate_levels(Title("Maximum rate of rejected packets")),
            "dropped": _packet_rate_levels(Title("Maximum rate of dropped packets")),
            "logged": _packet_rate_levels(Title("Maximum rate of logged packets")),
            "espencrypted": _packet_rate_levels(Title("Maximum rate of ESP encrypted packets")),
            "espdecrypted": _packet_rate_levels(Title("Maximum rate of ESP decrypted packets")),
        },
    )


rule_spec_checkpoint_packets = CheckParameters(
    name="checkpoint_packets",
    # weblate-flags: read-only, vendor-name
    title=Title("Check Point firewall packet rates"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_checkpoint_packets,
    condition=HostCondition(),
)
