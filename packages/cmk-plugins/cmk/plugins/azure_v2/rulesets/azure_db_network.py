#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        title=Title("Levels network"),
        elements={
            "ingress_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Network in"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="B"),
                    prefill_fixed_levels=DefaultValue((0.0, 0.0)),
                ),
            ),
            "egress_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Network out"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="B"),
                    prefill_fixed_levels=DefaultValue((0.0, 0.0)),
                ),
            ),
        },
    )


rule_spec_azure_db_network = CheckParameters(
    name="azure_v2_db_network",
    title=Title("Azure Network IO"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
