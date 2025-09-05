#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis replication monitoring"
        ),
        elements={
            "replication_unhealthy_status": DictElement(
                parameter_form=ServiceState(
                    title=Title("Service status when geo-replication link is unhealthy"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "replication_connectivity_lag_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum connectivity lag"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(0.0, 0.0)),
                )
            ),
        },
    )


rule_spec_azure_redis_replication = CheckParameters(
    name="azure_redis_replication",
    title=Title("Azure Redis replication"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
