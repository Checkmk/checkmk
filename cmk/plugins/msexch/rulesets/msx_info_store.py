#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _ms_to_s(values: object) -> dict:
    if not isinstance(values, dict):
        raise TypeError(values)

    # Introduced in a 2.3 patch release => remove in 2.5.0
    if "store_latency_s" in values:
        return values

    values["store_latency_s"] = tuple(x / 1000.0 for x in values.pop("store_latency"))
    values["clienttype_latency_s"] = tuple(x / 1000.0 for x in values.pop("clienttype_latency"))

    return values


def _item_spec() -> form_specs.String:
    return form_specs.String(
        help_text=Help("Specify the name of a store (This is either a mailbox or public folder)."),
        custom_validate=[form_specs.validators.LengthInRange(min_value=1)],
    )


def _parameter_formspec_msx_info_store():
    return form_specs.Dictionary(
        title=Title("Set levels"),
        migrate=_ms_to_s,
        elements={
            "store_latency_s": form_specs.DictElement(
                parameter_form=form_specs.SimpleLevels[float](
                    title=Title("Average latency for store requests"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    prefill_fixed_levels=form_specs.DefaultValue((0.04, 0.05)),
                    form_spec_template=form_specs.TimeSpan(
                        displayed_magnitudes=[form_specs.TimeMagnitude.MILLISECOND]
                    ),
                    migrate=form_specs.migrate_to_float_simple_levels,
                ),
                required=True,
            ),
            "clienttype_latency_s": form_specs.DictElement(
                parameter_form=form_specs.SimpleLevels[float](
                    title=Title("Average latency for client type requests"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    prefill_fixed_levels=form_specs.DefaultValue((0.04, 0.05)),
                    form_spec_template=form_specs.TimeSpan(
                        displayed_magnitudes=[form_specs.TimeMagnitude.MILLISECOND]
                    ),
                    migrate=form_specs.migrate_to_float_simple_levels,
                ),
                required=True,
            ),
            "clienttype_requests": form_specs.DictElement(
                parameter_form=form_specs.SimpleLevels[int](
                    title=Title("Maximum number of client type requests per second"),
                    level_direction=form_specs.LevelDirection.UPPER,
                    prefill_fixed_levels=form_specs.DefaultValue((60, 70)),
                    form_spec_template=form_specs.Integer(unit_symbol="requests"),
                    migrate=form_specs.migrate_to_integer_simple_levels,
                ),
                required=True,
            ),
        },
    )


rule_spec_msx_info_store = rule_specs.CheckParameters(
    title=Title("MS Exchange Information Store"),
    topic=rule_specs.Topic.APPLICATIONS,
    name="msx_info_store",
    parameter_form=_parameter_formspec_msx_info_store,
    condition=rule_specs.HostAndItemCondition(item_title=Title("Store"), item_form=_item_spec()),
)
