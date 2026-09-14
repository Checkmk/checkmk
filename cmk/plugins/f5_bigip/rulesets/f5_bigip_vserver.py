#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
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
    ServiceState,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_f5_bigip_vserver() -> Dictionary:
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
            "connections": DictElement(
                parameter_form=Levels[float](
                    title=Title("Total connections maximum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="connections"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((1000.0, 2000.0)),
                    predictive=PredictiveLevels(
                        reference_metric="connections",
                        prefill_abs_diff=DefaultValue((5.0, 8.0)),
                    ),
                    migrate=migrate_to_upper_float_levels,
                )
            ),
            "state": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map states"),
                    elements={
                        "is_disabled": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Is disabled"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "is_up_and_available": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Is up and available"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "is_currently_not_available": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Is currently not available"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                        "is_not_available": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Is not available"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                        ),
                        "availability_is_unknown": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Availability is unknown"),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                        ),
                        "is_unlicensed": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title("Is unlicensed"),
                                prefill=DefaultValue(ServiceState.UNKNOWN),
                            ),
                        ),
                        "children_pool_members_down_if_not_available": DictElement(
                            required=True,
                            parameter_form=ServiceState(
                                title=Title(
                                    "The children pool member(s) are down if VServer is not"
                                    " available"
                                ),
                                help_text=Help(
                                    "Overrides the state of a VServer that is not available"
                                    " because all of its pool members are down."
                                ),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                    },
                )
            ),
        },
    )


rule_spec_f5_bigip_vserver = CheckParameters(
    name="f5_bigip_vserver",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_f5_bigip_vserver,
    title=Title("F5 load balancer VServer"),
    condition=HostAndItemCondition(item_title=Title("VServer name")),
)
