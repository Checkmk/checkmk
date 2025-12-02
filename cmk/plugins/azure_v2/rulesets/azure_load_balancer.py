#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    IECMagnitude,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_byte_count_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Bytes transmitted"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(displayed_magnitudes=[IECMagnitude.BYTE]),
                    prefill_fixed_levels=DefaultValue((1024 * 1024, 1024 * 1024 * 10)),
                )
            ),
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Bytes transmitted (lower levels)"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=DataSize(displayed_magnitudes=[IECMagnitude.BYTE]),
                    prefill_fixed_levels=DefaultValue((1024, 512)),
                )
            ),
        }
    )


rule_spec_azure_v2_load_balancer_byte_count = CheckParameters(
    name="azure_v2_load_balancer_byte_count",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_byte_count_form,
    title=Title("Azure Load Balancer Byte Count"),
    condition=HostCondition(),
)


def _make_snat_form() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("SNAT usage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((75.0, 95.0)),
                )
            ),
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("SNAT usage (lower levels)"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((10.0, 5.0)),
                )
            ),
        }
    )


rule_spec_azure_v2_load_balancer_snat = CheckParameters(
    name="azure_v2_load_balancer_snat",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_snat_form,
    title=Title("Azure Load Balancer SNAT Consumption"),
    condition=HostCondition(),
)


def _make_health_form() -> Dictionary:
    return Dictionary(
        elements={
            "vip_availability": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Data path availability"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((90.0, 25.0)),
                )
            ),
            "health_probe": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Health probe status"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((90.0, 25.0)),
                )
            ),
        }
    )


rule_spec_azure_v2_load_balancer_health = CheckParameters(
    name="azure_v2_load_balancer_health",
    topic=Topic.APPLICATIONS,
    parameter_form=_make_health_form,
    title=Title("Azure Load Balancer Health"),
    condition=HostCondition(),
)
