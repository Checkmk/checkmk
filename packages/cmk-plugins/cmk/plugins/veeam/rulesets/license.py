#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_DAY = 60.0 * 60.0 * 24.0


def _expiry_levels(title: Title) -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=title,
        level_direction=LevelDirection.LOWER,
        form_spec_template=TimeSpan(
            displayed_magnitudes=[TimeMagnitude.DAY, TimeMagnitude.HOUR],
        ),
        prefill_levels_type=DefaultValue(LevelsType.FIXED),
        # TODO: proposed defaults, unvalidated against a real VBR instance. Revisit
        # once real license expiry/consumption data is available.
        prefill_fixed_levels=DefaultValue((30 * _DAY, 7 * _DAY)),
        migrate=migrate_to_float_simple_levels,
    )


def _parameter_form_veeam_license() -> Dictionary:
    return Dictionary(
        elements={
            "license_expiry": DictElement(
                parameter_form=_expiry_levels(Title("License expiry")),
            ),
            "support_expiry": DictElement(
                parameter_form=_expiry_levels(Title("Support expiry")),
            ),
            "consumption": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("License consumption"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    # TODO: proposed defaults, unvalidated against a real VBR instance.
                    # Revisit once real license expiry/consumption data is available.
                    prefill_fixed_levels=DefaultValue((80.0, 95.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_veeam_license = CheckParameters(
    name="veeam_license",
    title=Title("Veeam: License"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_license,
    condition=HostCondition(),
)
