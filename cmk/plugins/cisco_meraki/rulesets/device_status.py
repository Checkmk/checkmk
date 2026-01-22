#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "last_reported_upper_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Max time for last reported"),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((8 * 3600, 24 * 3600)),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR],
                        custom_validate=(NumberInRange(min_value=0),),
                    ),
                )
            ),
            "status_map": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map device status to monitoring state"),
                    elements={
                        "online": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "online"'),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "alerting": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "alerting"'),
                                prefill=DefaultValue(2),
                            )
                        ),
                        "offline": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "offline"'),
                                prefill=DefaultValue(1),
                            )
                        ),
                        "dormant": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "dormant"'),
                                prefill=DefaultValue(1),
                            )
                        ),
                    },
                )
            ),
        }
    )


rule_spec_cisco_meraki_org_device_status = CheckParameters(
    name="cisco_meraki_org_device_status",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki device status"),
    condition=HostCondition(),
)
