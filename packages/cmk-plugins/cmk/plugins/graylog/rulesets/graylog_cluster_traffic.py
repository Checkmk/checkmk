#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_DISPLAYED_MAGNITUDES = [
    IECMagnitude.BYTE,
    IECMagnitude.KIBI,
    IECMagnitude.MEBI,
    IECMagnitude.GIBI,
    IECMagnitude.TEBI,
]


def _parameter_valuespec_graylog_cluster_traffic() -> Dictionary:
    return Dictionary(
        elements={
            "input": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Absolute levels for input traffic"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "output": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Absolute levels for output traffic"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "decoded": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Absolute levels for decoded traffic"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=_DISPLAYED_MAGNITUDES),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_cluster_traffic = CheckParameters(
    name="graylog_cluster_traffic",
    title=Title("Graylog cluster traffic"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_cluster_traffic,
    condition=HostCondition(),
)
