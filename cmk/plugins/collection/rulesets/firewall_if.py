#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    Levels,
    LevelsType,
    migrate_to_upper_float_levels,
    PredictiveLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _drop_average_key(value: object) -> dict[str, object]:
    """drop the 'average' key. It never had any effect."""
    if not isinstance(value, dict):
        raise TypeError(f"Invalid value {value!r}")
    return {key: value for key, value in value.items() if key != "average"}


def _parameter_valuespec_firewall_if() -> Dictionary:
    return Dictionary(
        elements={
            "ipv4_in_blocked": DictElement(
                parameter_form=Levels(
                    title=Title("Levels for rate of incoming IPv4 packets blocked"),
                    form_spec_template=Float(unit_symbol="pkts/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((100.0, 10000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="ipv4_in_blocked",
                        prefill_abs_diff=DefaultValue((5, 8)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                ),
            ),
        },
        migrate=_drop_average_key,
    )


rule_spec_firewall_if = CheckParameters(
    name="firewall_if",
    title=Title("Firewall Interfaces"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_valuespec_firewall_if,
    condition=HostAndItemCondition(
        item_title=Title("Interface"),
        item_form=String(
            help_text=Help("The description of the interface as provided by the device")
        ),
    ),
)
