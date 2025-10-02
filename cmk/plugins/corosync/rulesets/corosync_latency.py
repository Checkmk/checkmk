#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_corosync_latency() -> Dictionary:
    return Dictionary(
        title=Title("Corosync Latency"),
        help_text=Help(
            "Configure warning and critical upper thresholds for Corosync link latency: "
            "both instantaneous maximum values and the averaged latency."
        ),
        elements={
            "latency_max": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Maximum latency (ms)"),
                    help_text=Help(
                        "Upper levels for the maximum latency. Defaults: 5 ms (WARN), 10 ms (CRIT)."
                    ),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.MILLISECOND],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(0.005, 0.01)),
                ),
            ),
            "latency_ave": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Average latency (ms)"),
                    help_text=Help(
                        "Upper levels for the average latency. Defaults: 5 ms (WARN), 10 ms (CRIT)."
                    ),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.MILLISECOND],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue(value=(0.005, 0.01)),
                ),
            ),
        },
    )


rule_spec_corosync_latency = CheckParameters(
    title=Title("Corosync Latency"),
    topic=Topic.NETWORKING,
    name="corosync_latency",
    parameter_form=_parameter_form_corosync_latency,
    condition=HostAndItemCondition(item_title=Title("Corosync Link")),
)
