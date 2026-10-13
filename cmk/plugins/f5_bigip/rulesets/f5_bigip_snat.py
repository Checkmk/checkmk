#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    Levels,
    LevelsType,
    migrate_to_lower_float_levels,
    migrate_to_upper_float_levels,
    PredictiveLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_f5_bigip_snat() -> Dictionary:
    return Dictionary(
        elements={
            "if_in_octets": DictElement(
                parameter_form=Levels[float](
                    title=Title("Incoming traffic maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000000.0, 2000000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_in_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_in_octets_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Incoming traffic minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000.0, 100.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_in_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
            "if_out_octets": DictElement(
                parameter_form=Levels[float](
                    title=Title("Outgoing traffic maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000000.0, 2000000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_out_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_out_octets_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Outgoing traffic minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000.0, 100.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_out_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
            "if_total_octets": DictElement(
                parameter_form=Levels[float](
                    title=Title("Total traffic maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((2000000.0, 4000000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_total_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_total_octets_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Total traffic minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="bytes/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((2000.0, 200.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_total_octets",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
            "if_in_pkts": DictElement(
                parameter_form=Levels[float](
                    title=Title("Incoming packets maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((10000.0, 20000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_in_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_in_pkts_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Incoming packets minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((100.0, 10.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_in_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
            "if_out_pkts": DictElement(
                parameter_form=Levels[float](
                    title=Title("Outgoing packets maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((10000.0, 20000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_out_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_out_pkts_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Outgoing packets minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((100.0, 10.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_out_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
            "if_total_pkts": DictElement(
                parameter_form=Levels[float](
                    title=Title("Total packets maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((20000.0, 40000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_total_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "if_total_pkts_lower": DictElement(
                parameter_form=Levels[float](
                    title=Title("Total packets minimum"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="packets/s"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((200.0, 20.0)),
                    predictive=PredictiveLevels(
                        reference_metric="if_total_pkts",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_lower_float_levels,
                )
            ),
        },
    )


rule_spec_f5_bigip_snat = CheckParameters(
    name="f5_bigip_snat",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_f5_bigip_snat,
    title=Title("F5 load balancer source NAT"),
    condition=HostAndItemCondition(item_title=Title("Source NAT name")),
)
