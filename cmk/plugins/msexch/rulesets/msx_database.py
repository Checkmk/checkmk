#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _ms_to_s(values: object) -> dict:
    if not isinstance(values, dict):
        raise TypeError(values)

    # Introduced in a 2.3 patch release => remove in 2.5.0
    if "read_attached_latency_s" in values:
        return values

    values["read_attached_latency_s"] = tuple(
        x / 1000.0 for x in values.pop("read_attached_latency")
    )
    values["read_recovery_latency_s"] = tuple(
        x / 1000.0 for x in values.pop("read_recovery_latency")
    )
    values["write_latency_s"] = tuple(x / 1000.0 for x in values.pop("write_latency"))
    values["log_latency_s"] = tuple(x / 1000.0 for x in values.pop("log_latency"))

    return values


def _upper_levels(title: Title, prefill: tuple[float, float]) -> form_specs.SimpleLevels[float]:
    return form_specs.SimpleLevels[float](
        title=title,
        level_direction=form_specs.LevelDirection.UPPER,
        prefill_fixed_levels=form_specs.DefaultValue(prefill),
        form_spec_template=form_specs.TimeSpan(
            displayed_magnitudes=[form_specs.TimeMagnitude.MILLISECOND]
        ),
        migrate=form_specs.migrate_to_float_simple_levels,
    )


def _item_spec() -> form_specs.String:
    return form_specs.String(
        help_text=Help("Specify database names that the rule should apply to."),
        custom_validate=[form_specs.validators.LengthInRange(min_value=1)],
    )


def _parameter_formspec_msx_database():
    return form_specs.Dictionary(
        title=Title("Set levels"),
        migrate=_ms_to_s,
        elements={
            "read_attached_latency_s": form_specs.DictElement(
                parameter_form=_upper_levels(
                    Title("I/O database reads (attached) average latency"),
                    (0.2, 0.25),
                ),
                required=True,
            ),
            "read_recovery_latency_s": form_specs.DictElement(
                parameter_form=_upper_levels(
                    Title("I/O database reads (recovery) average latency"),
                    (0.15, 0.2),
                ),
                required=True,
            ),
            "write_latency_s": form_specs.DictElement(
                parameter_form=_upper_levels(
                    Title("I/O database writes (attached) average latency"),
                    (0.04, 0.05),
                ),
                required=True,
            ),
            "log_latency_s": form_specs.DictElement(
                parameter_form=_upper_levels(
                    Title("I/O log writes average latency"), (0.005, 0.01)
                ),
                required=True,
            ),
        },
    )


rule_spec_msx_database = rule_specs.CheckParameters(
    title=Title("MS Exchange Database"),
    topic=rule_specs.Topic.APPLICATIONS,
    name="msx_database",
    parameter_form=_parameter_formspec_msx_database,
    condition=rule_specs.HostAndItemCondition(
        item_title=Title("Database name"), item_form=_item_spec()
    ),
)
