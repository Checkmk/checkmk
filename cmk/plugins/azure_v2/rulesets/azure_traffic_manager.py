#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_qps_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Queries per second"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=DefaultValue((10.0, 50.0)),
                )
            ),
        }
    )


rule_spec_azure_v2_traffic_manager_qps = CheckParameters(
    name="azure_v2_traffic_manager_qps",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_qps_form,
    title=Title("Azure Traffic Manager QPS"),
    condition=HostCondition(),
)


def _make_probe_state_form() -> Dictionary:
    return Dictionary(
        elements={
            "custom_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when probe is not OK"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
        }
    )


rule_spec_azure_v2_traffic_manager_probe_state = CheckParameters(
    name="azure_v2_traffic_manager_probe_state",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_probe_state_form,
    title=Title("Azure Traffic Manager Probe State"),
    condition=HostCondition(),
)
