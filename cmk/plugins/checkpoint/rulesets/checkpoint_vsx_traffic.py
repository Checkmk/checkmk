#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    Levels,
    migrate_to_upper_integer_levels,
    PredictiveLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_checkpoint_vsx_traffic():
    return Dictionary(
        elements={
            "bytes_accepted": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Maximum rate of bytes accepted"),
                    form_spec_template=Integer(label=Label("bytes/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "bytes_dropped": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Maximum rate of bytes dropped"),
                    form_spec_template=Integer(label=Label("bytes/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "bytes_rejected": DictElement(
                required=False,
                parameter_form=Levels(
                    title=Title("Maximum rate of bytes rejected"),
                    form_spec_template=Integer(label=Label("bytes/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
        }
    )


rule_spec_checkpoint_vsx_traffic = CheckParameters(
    name="checkpoint_vsx_traffic",
    title=Title("Check Point VSID traffic rate"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_valuespec_checkpoint_vsx_traffic,
    condition=HostAndItemCondition(item_title=Title("VSID")),
)
