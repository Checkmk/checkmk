#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_prism_protection_policies() -> Dictionary:
    return Dictionary(
        elements={
            "recovery_point_age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age of the newest recovery point of a VM"),
                    help_text=Help(
                        "Levels on the age of the newest recovery point of each VM the policy "
                        "protects, as a multiple of the policy's recovery point objective (RPO). "
                        "In normal operation the newest recovery point is up to one RPO old. "
                        "For a VM without a recovery point, the age counts from when the check "
                        "first saw the VM."
                    ),
                    form_spec_template=Float(
                        label=Label("times the RPO"),
                        # Below one RPO even a healthy VM would alert
                        custom_validate=(NumberInRange(min_value=1.0),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((1.5, 2.0)),
                ),
                required=True,
            ),
            "replication_states": DictElement(
                parameter_form=Dictionary(
                    title=Title("States of the replication of a VM to a remote location"),
                    help_text=Help(
                        "Only VMs of policies that replicate to a remote location "
                        "synchronously or every 1 to 15 minutes have a replication state. "
                        "The v4 API reports none for hourly or longer schedules."
                    ),
                    elements={
                        "in_sync": DictElement(
                            parameter_form=ServiceState(
                                title=Title("In sync"), prefill=DefaultValue(ServiceState.OK)
                            ),
                            required=True,
                        ),
                        "syncing": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Syncing"), prefill=DefaultValue(ServiceState.OK)
                            ),
                            required=True,
                        ),
                        "out_of_sync": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Out of sync"),
                                help_text=Help(
                                    "The replication schedule is disabled and nothing replicates."
                                ),
                                prefill=DefaultValue(ServiceState.WARN),
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
            "replication_paused": DictElement(
                parameter_form=ServiceState(
                    title=Title("State if the replication of a schedule is paused"),
                    help_text=Help(
                        "Only schedules with synchronous replication (RPO of 0) can be paused."
                    ),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
                required=True,
            ),
        },
    )


rule_spec_prism_protection_policies = CheckParameters(
    name="prism_protection_policies",
    title=Title("Nutanix protection policies"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_parameter_form_prism_protection_policies,
    condition=HostAndItemCondition(item_title=Title("Protection policy")),
)
