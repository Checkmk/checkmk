#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_veeam_backup_jobs() -> Dictionary:
    return Dictionary(
        elements={
            "disabled_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when the job is disabled"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "age": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since last run"),
                    help_text=Help(
                        "The levels are not applied to jobs that have never run, or to disabled "
                        'jobs, whose state is set with "State when the job is disabled".'
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((86400.0, 172800.0)),
                ),
            ),
        },
    )


rule_spec_veeam_backup_jobs = CheckParameters(
    name="veeam_backup_jobs",
    title=Title("Veeam: Backup job"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_backup_jobs,
    condition=HostAndItemCondition(item_title=Title("Job name")),
)
