#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This check monitors the status of time synchronization for Windows hosts."),
        elements={
            "states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("State based on status of last sync attempt"),
                    help_text=Help(
                        "Time syncs especially against public NTP servers can fail in various "
                        "ways throughout the course of the NTP lifecycle and therefore we do not "
                        "alert by default when a sync fails (preferring instead to alert when too "
                        "much time has elapsed before a successful sync). However, in some "
                        "environments, it might be useful to know right away when a sync fails. "
                        "The state of various kinds of failures can therefore be configured here."
                    ),
                    elements={
                        "never_synced": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("Never synchronized"),
                                help_text=Help(
                                    "When the reference ID and state machine value are both 0, it "
                                    "usually means that the service has not synced since starting. "
                                    "The reported state in this scenario can be configured here."
                                ),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "no_data": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("No data from time provider"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "stale_data": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("Stale data received from time provider"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "time_diff_too_large": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("Difference in time from provider was too large"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                        "shutting_down": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("The time service was shutting down"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                        ),
                    },
                ),
            ),
            "stratum": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Stratum"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((5, 10)),
                ),
            ),
            "offset": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Time offset"),
                    help_text=Help(
                        "When the time offset on the last sync was worse (in either direction) "
                        "than the specified parameters, go into WARN or CRIT status."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue((0.8, 1.0)),
                ),
            ),
            "time_since_last_successful_sync": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum time since the last successful sync"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(0.0, 0.0)),
                ),
            ),
        },
    )


rule_spec_w32time = CheckParameters(
    name="w32time",
    title=Title("Windows time service"),
    topic=Topic.WINDOWS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
