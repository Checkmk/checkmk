#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec_check_parameters = CheckParameters(
    title=Title("Splunk Jobs"),
    topic=Topic.APPLICATIONS,
    parameter_form=lambda: Dictionary(
        elements={
            "job_count": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of jobs"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "failed_count": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of failed jobs"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "zombie_count": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of zombie jobs"),
                    help_text=Help(
                        "Splunk labels a job a zombie when the job is no longer running,"
                        "but it did not declare explicitly that it has finished its work."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
        },
    ),
    name="splunk_jobs",
    condition=HostCondition(),
)
