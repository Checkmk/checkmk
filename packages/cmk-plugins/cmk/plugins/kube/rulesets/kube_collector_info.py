#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    Percentage,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_cache_health(title: Title) -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=title,
        prefill=DefaultValue("percentage"),
        elements=[
            CascadingSingleChoiceElement(
                name="percentage",
                title=Title("Percentual levels"),
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=InputHint(value=(80, 95)),
                ),
            ),
            CascadingSingleChoiceElement(
                name="absolute",
                title=Title("Absolute levels"),
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint(value=(20_000, 45_000)),
                ),
            ),
        ],
    )


def _parameter_form_kube_collector_info() -> Dictionary:
    return Dictionary(
        elements={
            "machine_metrics": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title(
                        "Monitoring state if the cluster collector reports no machine metrics"
                    ),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "container_metrics_cache_size": DictElement(
                required=False,
                parameter_form=_parameter_form_cache_health(
                    Title("Upper levels on container metrics cache size")
                ),
            ),
            "machine_sections_cache_size": DictElement(
                required=False,
                parameter_form=_parameter_form_cache_health(
                    Title("Upper levels on machine sections cache size")
                ),
            ),
        },
    )


rule_spec_kube_collector_info = CheckParameters(
    name="kube_collector_info",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_kube_collector_info,
    title=Title("Kubernetes Collector info"),
    condition=HostCondition(),
)
