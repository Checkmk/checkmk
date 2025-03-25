#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "seconds_behind_master": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Max. time behind the master"),
                    help_text=Help(
                        "Compares the time which the slave can be behind the master. "
                        "This rule makes the check raise warning/critical states if the time is equal to "
                        "or above the configured levels."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        )
                    ),
                    migrate=migrate_to_float_simple_levels,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            )
        },
    )


rule_spec_mysql_replica_slave = CheckParameters(
    name="mysql_slave",
    title=Title("MySQL replica/slave"),
    topic=Topic.DATABASES,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(
        item_title=Title("Instance"),
        item_form=String(
            help_text=Help("Only needed if you have multiple MySQL instances on one server"),
        ),
    ),
)
