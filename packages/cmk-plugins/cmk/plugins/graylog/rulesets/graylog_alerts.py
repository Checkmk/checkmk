#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_graylog_alerts() -> Dictionary:
    return Dictionary(
        elements={
            "alerts_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total alerts count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "alerts_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total alerts count lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "alerts_in_range_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of alerts in defined time span upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="alerts"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "alerts_in_range_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of alerts in defined time span lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="alerts"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_alerts = CheckParameters(
    name="graylog_alerts",
    title=Title("Graylog alerts"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_alerts,
    condition=HostCondition(),
)
