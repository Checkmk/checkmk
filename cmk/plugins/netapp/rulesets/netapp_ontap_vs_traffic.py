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
    LevelDirection,
    LevelsType,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _latency_levels(title: Title) -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=title,
        level_direction=LevelDirection.UPPER,
        form_spec_template=TimeSpan(
            displayed_magnitudes=(TimeMagnitude.MILLISECOND, TimeMagnitude.SECOND),
        ),
        prefill_levels_type=DefaultValue(LevelsType.NONE),
        prefill_fixed_levels=InputHint(value=(0.001, 0.005)),
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help("The service reports the latency of every protocol the SVM serves."),
        elements={
            "read_latency_levels": DictElement(
                parameter_form=_latency_levels(Title("Levels on the read latency")),
            ),
            "write_latency_levels": DictElement(
                parameter_form=_latency_levels(Title("Levels on the write latency")),
            ),
        },
    )


rule_spec_netapp_ontap_vs_traffic = CheckParameters(
    name="netapp_ontap_vs_traffic",
    title=Title("NetApp SVM traffic"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("SVM name")),
)
