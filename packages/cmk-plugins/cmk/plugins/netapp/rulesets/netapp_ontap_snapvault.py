#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _lag_time_span() -> TimeSpan:
    return TimeSpan(
        displayed_magnitudes=[
            TimeMagnitude.DAY,
            TimeMagnitude.HOUR,
            TimeMagnitude.MINUTE,
            TimeMagnitude.SECOND,
        ],
    )


def _migrate_policy_lag_time(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    return [
        entry
        if isinstance(entry, dict)
        else {
            "policy_name": entry[0],
            "levels": migrate_to_float_simple_levels(entry[1]),
        }
        for entry in value
    ]


def _parameter_form_snapvault() -> Dictionary:
    return Dictionary(
        elements={
            "lag_time": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Lag time (default levels)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=_lag_time_span(),
                    prefill_fixed_levels=InputHint((86400.0, 172800.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "policy_lag_time": DictElement(
                parameter_form=List(
                    title=Title("Lag time (policy-specific levels)"),
                    help_text=Help(
                        "Here, you can specify levels for different policies which overrule "
                        "the default lag time levels."
                    ),
                    element_template=Dictionary(
                        elements={
                            "policy_name": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Policy name"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                            "levels": DictElement(
                                required=True,
                                parameter_form=SimpleLevels[float](
                                    title=Title("Maximum lag time"),
                                    level_direction=LevelDirection.UPPER,
                                    form_spec_template=_lag_time_span(),
                                    prefill_fixed_levels=InputHint((86400.0, 172800.0)),
                                ),
                            ),
                        },
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=_migrate_policy_lag_time,
                ),
            ),
        },
    )


rule_spec_snapvault = CheckParameters(
    name="snapvault",
    title=Title("NetApp SnapVault / SnapMirror"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_snapvault,
    condition=HostAndItemCondition(item_title=Title("Destination")),
)


def _discovery_form_snapvault() -> Dictionary:
    return Dictionary(
        elements={
            "exclude_destination_vserver": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Exclude destination vserver"),
                    help_text=Help(
                        "The service name of SnapVault services is composed of the destination "
                        "vserver (SVM) and the destination volume by default. Check this box if "
                        "you would like to use the destination volume as the service name on its "
                        "own. Please be advised that this may lead to a service name that is not "
                        "unique, resulting in some services which are not shown."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_discovery_snapvault = DiscoveryParameters(
    name="discovery_snapvault",
    title=Title("NetApp SnapVault discovery"),
    topic=Topic.STORAGE,
    parameter_form=_discovery_form_snapvault,
)
