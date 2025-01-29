#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import form_specs, rule_specs, Title


def _ms_to_s(values: object) -> dict:
    if not isinstance(values, dict):
        raise TypeError(values)

    # Introduced in a 2.3 patch release => remove in 2.5.0
    if "latency_s" in values:
        return values

    values["latency_s"] = tuple(x / 1000.0 for x in values.pop("latency"))

    return values


def _parameter_formspec_msx_rpcclientaccess():
    return form_specs.Dictionary(
        title=Title("Set levels"),
        migrate=_ms_to_s,
        elements={
            "latency_s": form_specs.DictElement(
                parameter_form=form_specs.SimpleLevels[float](
                    title=Title("Average latency for RPC requests"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    prefill_fixed_levels=form_specs.DefaultValue((0.2, 0.25)),
                    form_spec_template=form_specs.TimeSpan(
                        displayed_magnitudes=[form_specs.TimeMagnitude.MILLISECOND]
                    ),
                    migrate=form_specs.migrate_to_float_simple_levels,
                ),
                required=True,
            ),
            "requests": form_specs.DictElement(
                parameter_form=form_specs.SimpleLevels[int](
                    title=Title("Maximum number of RPC requests per second"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    prefill_fixed_levels=form_specs.DefaultValue((30, 40)),
                    form_spec_template=form_specs.Integer(unit_symbol="requests"),
                    migrate=form_specs.migrate_to_integer_simple_levels,
                ),
                required=True,
            ),
        },
    )


rule_spec_msx_rpcclientaccess = rule_specs.CheckParameters(
    title=Title("MS Exchange RPC Client Access"),
    topic=rule_specs.Topic.APPLICATIONS,
    name="msx_rpcclientaccess",
    parameter_form=_parameter_formspec_msx_rpcclientaccess,
    condition=rule_specs.HostCondition(),
)
