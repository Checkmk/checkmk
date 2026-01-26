#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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


def podman_container_restarts() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Here you can configure absolute levels for total restart count and last hour restarts."
        ),
        elements={
            "restarts_total": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Total restarts"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "restarts_last_hour": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Last hour restarts"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
    )


rule_spec_podman_container_restarts = CheckParameters(
    name="podman_container_restarts",
    title=Title("Podman container restarts"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_container_restarts,
    condition=HostCondition(),
)
