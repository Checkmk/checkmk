#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-04
# File  : device_status.py (WATO)

# 2024-06-30: moved power supply part to cisco_meraki_org_device_status_ps.py (shadow built-in file)
# 2025-03-30: moved to ruleset APIv1

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    ServiceState,
    SimpleLevels,
    LevelsType,
    LevelDirection,
    TimeSpan,
    TimeMagnitude,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic
from cmk.rulesets.v1.form_specs.validators import NumberInRange


def _migrate_to_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)

    raise TypeError(value)


#
# Cisco Meraki Device Status
#
def _parameter_form_cisco_meraki_device_status():
    return Dictionary(
        elements={
            'last_reported_upper_levels': DictElement(
                parameter_form=SimpleLevels(
                    title=Title('Max time for last reported'),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((8 * 3600, 24 * 3600)),
                    level_direction=LevelDirection.UPPER,
                    # migrate=migrate_to_integer_simple_levels,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR],
                        custom_validate=(NumberInRange(min_value=0, ),),
                        migrate=_migrate_to_float,
                    )
                )),
            'status_map': DictElement(
                parameter_form=Dictionary(
                    title=Title('Map device status to monitoring state'),
                    elements={
                        "online": DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "online"'),
                                prefill=DefaultValue(0),
                            )),
                        'alerting': DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "alerting"'),
                                prefill=DefaultValue(2),
                            )),
                        'offline': DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "offline"'),
                                prefill=DefaultValue(1),
                            )),
                        'dormant': DictElement(
                            parameter_form=ServiceState(
                                title=Title('Monitoring state for device state "dormant"'),
                                prefill=DefaultValue(1),
                            )),
                    }
                ))
        }
    )


rule_spec_cisco_meraki_device_status = CheckParameters(
    title=Title("Cisco Meraki Device status"),
    name="cisco_meraki_device_status",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form_cisco_meraki_device_status,
    condition=HostCondition(),
)
