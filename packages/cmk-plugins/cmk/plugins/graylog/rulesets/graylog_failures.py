#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
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


def _parameter_valuespec_graylog_failures() -> Dictionary:
    return Dictionary(
        elements={
            "failures": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total index failure count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "failures_last": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Index failure in the defined time range upper levels"),
                    help_text=Help(
                        "Here, you can set levels on failures in the time range "
                        "specified in the data source (default: 30 min)."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_failures = CheckParameters(
    name="graylog_failures",
    title=Title("Graylog index failures"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_failures,
    condition=HostCondition(),
)
