#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_zorp_connections():
    return Dictionary(
        elements={
            "levels": DictElement(
                required=True,  # it's the only one.
                parameter_form=SimpleLevels(
                    title=Title("Threshold on number of connections"),
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((15, 20)),
                ),
            )
        }
    )


rule_spec_zorp_connections = CheckParameters(
    name="zorp_connections",
    title=Title("Zorp connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_zorp_connections,
    condition=HostCondition(),
)
