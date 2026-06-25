#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_integer_simple_levels,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_graylog_streams() -> Dictionary:
    return Dictionary(
        elements={
            "stream_count_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of streams lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_count_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of streams upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="streams"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stream_disabled": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when one of the streams is in state disabled"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


rule_spec_graylog_streams = CheckParameters(
    name="graylog_streams",
    title=Title("Graylog streams"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_streams,
    condition=HostCondition(),
)
