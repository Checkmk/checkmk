#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate_params(params: object) -> Mapping[str, object]:
    if not isinstance(params, dict):
        return {}
    return {key: migrate_to_float_simple_levels(value) for key, value in params.items()}


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "To obtain the data required for this check, please configure"
            ' the data source program "Microsoft Azure".'
        ),
        migrate=_migrate_params,
        elements={
            "avg_response_time_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for average response time"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="s"),
                    prefill_fixed_levels=DefaultValue((1.0, 10.0)),
                ),
            ),
            "error_rate_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for rate of server errors"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/s"),
                    prefill_fixed_levels=DefaultValue((0.01, 0.04)),
                ),
            ),
            "cpu_time_percent_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for CPU time"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=DefaultValue((85.0, 95.0)),
                ),
            ),
        },
    )


rule_spec_azure_sites = CheckParameters(
    name="webserver",
    title=Title("Azure web servers (IIS) (deprecated)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Name of the service")),
)
