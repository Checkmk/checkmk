#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for Azure subscription info."),
        elements={
            "remaining_reads": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on remaining API reads"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "remaining_reads_unknown_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State if remaining API reads are unknown"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "resource_pinning": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Resource pinning: Ensure monitored resources are unchanged"),
                    elements=[
                        SingleChoiceElement(
                            name="true", title=Title("Warn if resources appear or vanish")
                        ),
                        SingleChoiceElement(
                            name="false", title=Title("Silently ignore new or missing resources")
                        ),
                    ],
                ),
            ),
        },
        ignored_elements=("discovered_resources",),
    )


rule_spec_azure_subscription_info = CheckParameters(
    name="azure_v2_subscription_info",
    title=Title("Azure subscription info"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
