#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_rulespec_acme_sbc_snmp() -> Dictionary:
    return Dictionary(
        elements={
            "lower_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels on health status score in percent"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((75, 50)),
                    migrate=migrate_to_integer_simple_levels,
                ),
                required=True,
            )
        }
    )


rule_spec_acme_sbc_snmp = CheckParameters(
    parameter_form=_parameter_rulespec_acme_sbc_snmp,
    name="acme_sbc_snmp",
    title=Title("ACME SBC health"),
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
)
