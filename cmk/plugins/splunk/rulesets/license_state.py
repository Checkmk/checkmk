#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

rule_spec_check_parameters = CheckParameters(
    title=Title("Splunk License State"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            "state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State if license is expired"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "expiration_time": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Time until license expiration"),
                    help_text=Help(
                        "Remaining time (seconds) until the license expires. The defaults equate"
                        "to 14 days (warning) and 7 days (critical)."
                    ),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint(
                        value=(
                            14 * 24 * 60 * 60,  # 14 days
                            7 * 24 * 60 * 60,  # 7 days
                        )
                    ),
                )
            ),
        },
    ),
    name="splunk_license_state",
    condition=HostAndItemCondition(item_title=Title("Name of license")),
)
