#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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


def _parameter_valuespec_checkpoint_vsx_packets():
    return Dictionary(
        elements={
            "packets": DictElement(
                parameter_form=Levels(
                    title=Title("Maximum rate for total number of packets"),
                    form_spec_template=Integer(label=Label("packets/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "packets_accepted": DictElement(
                parameter_form=Levels(
                    title=Title("Maximum rate of accepted packets"),
                    form_spec_template=Integer(label=Label("packets/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "packets_rejected": DictElement(
                parameter_form=Levels(
                    title=Title("Maximum rate of rejected packets"),
                    form_spec_template=Integer(label=Label("packets/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "packets_dropped": DictElement(
                parameter_form=Levels(
                    title=Title("Maximum rate of dropped packets"),
                    form_spec_template=Integer(label=Label("packets/sec")),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((100000, 200000)),
                    predictive=PredictiveLevels(
                        reference_metric="packets",
                        prefill_abs_diff=DefaultValue((5000, 10000)),
                    ),
                    migrate=migrate_to_upper_integer_levels,
                ),
            ),
            "packets_logged": DictElement(
                parameter_form=Levels(
                    title=Title("Maximum rate of sent logs"),
                    form_spec_template=Integer(label=Label("packets/sec")),
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


rule_spec_checkpoint_vsx_packets = CheckParameters(
    name="checkpoint_vsx_packets",
    title=Title("Check Point VSID packet rate"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_valuespec_checkpoint_vsx_packets,
    condition=HostAndItemCondition(item_title=Title("VSID")),
)
