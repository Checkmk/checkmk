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
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_DAY = 86400.0


def _age_levels(title: Title) -> DictElement[SimpleLevelsConfigModel[float]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            level_direction=LevelDirection.UPPER,
            form_spec_template=TimeSpan(
                displayed_magnitudes=(
                    TimeMagnitude.DAY,
                    TimeMagnitude.HOUR,
                    TimeMagnitude.MINUTE,
                ),
            ),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue((_DAY, 7 * _DAY)),
            migrate=migrate_to_float_simple_levels,
        ),
    )


def _parameter_form_kaspersky_av_client() -> Dictionary:
    return Dictionary(
        elements={
            "signature_age": _age_levels(Title("Upper levels for the age of the signatures")),
            "fullscan_age": _age_levels(Title("Upper levels for the age of the last fullscan")),
        },
    )


rule_spec_kaspersky_av_client = CheckParameters(
    name="kaspersky_av_client",
    # weblate-flags: read-only, vendor-name
    title=Title("Kaspersky Anti-Virus time settings"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_kaspersky_av_client,
    condition=HostCondition(),
)
