#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for the database CPU usage"),
        elements={
            "avg_response_time_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for average response time"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="s"),
                    prefill_fixed_levels=DefaultValue((1.0, 10.0)),
                ),
            ),
            "error_rate_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for rate of server errors"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="1/2"),
                    prefill_fixed_levels=DefaultValue((0.01, 0.04)),
                ),
            ),
            "cpu_time_percent_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for CPU time"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    prefill_fixed_levels=DefaultValue((85.0, 95.0)),
                ),
            ),
        },
    )


rule_spec_azure_webservers = CheckParameters(
    name="azure_v2_webserver",
    title=Title("Azure web servers (IIS)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
