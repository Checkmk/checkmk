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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_rulespec_mssql_connections() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the number of active database connections"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((20, 50)),
                    migrate=migrate_to_integer_simple_levels,
                ),
                required=False,
            ),
        }
    )


rule_spec_mssql_connections = CheckParameters(
    name="mssql_connections",
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Database identifier")),
    parameter_form=_parameter_rulespec_mssql_connections,
    title=Title("MSSQL Connections"),
)
