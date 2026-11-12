#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_prism_protection_policies() -> Dictionary:
    return Dictionary(
        elements={
            "recovery_point_age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age of the newest recovery point of a VM"),
                    help_text=Help(
                        "Levels on the age of the newest recovery point of each VM the policy "
                        "protects, as a multiple of the policy's recovery point objective (RPO). "
                        "In normal operation the newest recovery point is up to one RPO old. "
                        "For a VM without a recovery point, the age counts from when the check "
                        "first saw the VM."
                    ),
                    form_spec_template=Float(
                        label=Label("times the RPO"),
                        # Below one RPO even a healthy VM would alert
                        custom_validate=(NumberInRange(min_value=1.0),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((1.5, 2.0)),
                ),
                required=True,
            ),
        },
    )


rule_spec_prism_protection_policies = CheckParameters(
    name="prism_protection_policies",
    title=Title("Nutanix protection policies"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_protection_policies,
    condition=HostAndItemCondition(item_title=Title("Protection policy")),
)
