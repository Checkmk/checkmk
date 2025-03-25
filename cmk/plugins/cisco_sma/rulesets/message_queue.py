#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    Percentage,
    ServiceState,
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _queue_form() -> Dictionary:
    return Dictionary(
        elements={
            "monitoring_status_memory_available": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status if memory is available"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "monitoring_status_memory_shortage": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status in case of memory shortage"),
                    prefill=DefaultValue(ServiceState.WARN),
                )
            ),
            "monitoring_status_queue_full": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring status if memory is full"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "levels_queue_utilization": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels(
                    title=Title("Levels on queue utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=InputHint((80.0, 90.0)),
                ),
            ),
            "levels_queue_length": DictElement[SimpleLevelsConfigModel[int]](
                parameter_form=SimpleLevels(
                    title=Title("Levels on total number of messages in queue"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((500, 1000)),
                ),
            ),
            "levels_oldest_message_age": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels(
                    title=Title("Levels on age of oldest message"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        label=Label(""),
                        displayed_magnitudes=[
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                        prefill=DefaultValue(58.0),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
        }
    )


rule_spec_queue = CheckParameters(
    name="cisco_sma_message_queue",
    title=Title("Cisco SMA queue"),
    topic=Topic.APPLICATIONS,
    parameter_form=_queue_form,
    condition=HostCondition(),
)
