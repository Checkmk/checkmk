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
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_DAY = 24 * 3600


def _parameter_form_wlan_controllers_clients() -> Dictionary:
    return Dictionary(
        elements={
            "clients": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Maximum number of clients"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                ),
            )
        },
    )


rule_spec_cisco_prime_wlan_controller_clients = CheckParameters(
    name="cisco_prime_wlan_controller_clients",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_title=Title("Clients")),
    parameter_form=_parameter_form_wlan_controllers_clients,
    title=Title("Cisco Prime WLAN Controller Clients"),
)


def _parameter_form_wlan_controllers_access_points() -> Dictionary:
    return Dictionary(
        elements={
            "access_points": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Maximum number of access points"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                ),
            ),
        },
    )


rule_spec_cisco_prime_wlan_controller_access_points = CheckParameters(
    name="cisco_prime_wlan_controller_access_points",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_title=Title("Access points")),
    parameter_form=_parameter_form_wlan_controllers_access_points,
    title=Title("Cisco Prime WLAN Controller Access Points"),
)


def _parameter_form_wlan_controllers_last_backup() -> Dictionary:
    return Dictionary(
        elements={
            "last_backup": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since last backup"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    prefill_fixed_levels=DefaultValue((7 * _DAY, 30 * _DAY)),
                    migrate=migrate_to_float_simple_levels,
                ),
            )
        },
    )


rule_spec_cisco_prime_wlan_controller_last_backup = CheckParameters(
    name="cisco_prime_wlan_controller_last_backup",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_title=Title("Last backup")),
    parameter_form=_parameter_form_wlan_controllers_last_backup,
    title=Title("Cisco Prime WLAN Controller Last Backup"),
)
