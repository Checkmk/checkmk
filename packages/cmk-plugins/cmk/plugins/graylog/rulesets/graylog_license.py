#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    migrate_to_float_simple_levels,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_graylog_license() -> Dictionary:
    return Dictionary(
        elements={
            "no_enterprise": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when no enterprise license is installed"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "expired": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license is expired"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "violated": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license state is violated"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "valid": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license is not valid"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "traffic_exceeded": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license traffic is exceeded"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "cluster_not_covered": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license does not cover cluster"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "nodes_exceeded": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license nodes exceeded"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "remote_checks_failed": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when license remote check failed"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "expiration": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time until license expiration"),
                    help_text=Help("Remaining days until the Graylog license expires"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_fixed_levels=DefaultValue((14 * 24 * 60 * 60.0, 7 * 24 * 60 * 60.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_license = CheckParameters(
    name="graylog_license",
    title=Title("Graylog license"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_license,
    condition=HostCondition(),
)
