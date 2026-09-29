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
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_HOUR = 60.0 * 60.0


def _parameter_form_veeam_config_backup() -> Dictionary:
    return Dictionary(
        elements={
            "disabled_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when configuration backup is disabled"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "age": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since last successful backup"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    # TODO: thresholds are proposed and unvalidated. The reference
                    # PowerShell implementation instead uses 7/14 days, looser than a
                    # daily backup schedule warrants — this disagreement needs settling.
                    prefill_fixed_levels=DefaultValue((48 * _HOUR, 96 * _HOUR)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_veeam_config_backup = CheckParameters(
    name="veeam_config_backup",
    title=Title("Veeam: Configuration backup"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_config_backup,
    condition=HostCondition(),
)
