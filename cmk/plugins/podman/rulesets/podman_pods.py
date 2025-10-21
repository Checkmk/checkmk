#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


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


def _simple_levels_element(property: str) -> DictElement:
    """Create threshold levels for upper and lower bounds for a specific pod state."""
    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title(f"{property.capitalize()} Podman pods"),  # pylint: disable=localization-of-non-literal-string
            elements={
                "levels_lower": DictElement(
                    parameter_form=SimpleLevels(
                        title=Title(f"Lower threshold on {property} number of Podman pods"),  # pylint: disable=localization-of-non-literal-string
                        form_spec_template=Integer(),
                        level_direction=LevelDirection.LOWER,
                        prefill_fixed_levels=InputHint((0, 0)),
                    ),
                ),
                "levels_upper": DictElement(
                    parameter_form=SimpleLevels(
                        title=Title(f"Upper threshold on {property} number of Podman pods"),  # pylint: disable=localization-of-non-literal-string
                        form_spec_template=Integer(),
                        level_direction=LevelDirection.UPPER,
                        prefill_fixed_levels=InputHint((0, 0)),
                    ),
                ),
            },
        ),
    )


def podman_pods() -> Dictionary:
    return Dictionary(
        help_text=Help("Thresholds for the podman pods service."),
        elements={
            "total": _simple_levels_element("total"),
            "running": _simple_levels_element("running"),
            "created": _simple_levels_element("created"),
            "stopped": _simple_levels_element("stopped"),
            "dead": _simple_levels_element("dead"),
            "exited": _simple_levels_element("exited"),
        },
    )


rule_spec_podman_pods = CheckParameters(
    name="podman_pods",
    title=Title("Podman Containers"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_pods,
    condition=HostCondition(),
)
