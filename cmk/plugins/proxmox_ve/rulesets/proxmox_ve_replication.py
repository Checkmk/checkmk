#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_proxmox_ve_replication():
    return Dictionary(
        elements={
            "time_since_last_replication": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper limit of time since last replication"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ]
                    ),
                    prefill_fixed_levels=InputHint(value=(60.0 * 60.0, 60.0 * 60.0 * 2.0)),
                ),
            ),
            "no_replications_state": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title(
                        "Service state when no replication jobs are configured on the cluster"
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        }
    )


rule_spec_proxmox_ve_replication = CheckParameters(
    name="proxmox_ve_replication",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_valuespec_proxmox_ve_replication,
    title=Title("Proxmox VE Replication"),
    condition=HostCondition(),
)
