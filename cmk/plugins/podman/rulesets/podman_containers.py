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
    """Create threshold levels for upper and lower bounds for a specific container state."""
    return DictElement(
        required=False,
        parameter_form=Dictionary(
            title=Title(  # astrein: disable=localization-checker
                f"{property.capitalize()} Podman containers"
            ),
            elements={
                "levels_lower": DictElement(
                    parameter_form=SimpleLevels(
                        title=Title(  # astrein: disable=localization-checker
                            f"Lower threshold on {property} number of Podman containers"
                        ),
                        form_spec_template=Integer(),
                        level_direction=LevelDirection.LOWER,
                        prefill_fixed_levels=InputHint((0, 0)),
                    ),
                ),
                "levels_upper": DictElement(
                    parameter_form=SimpleLevels(
                        title=Title(  # astrein: disable=localization-checker
                            f"Upper threshold on {property} number of Podman containers"
                        ),
                        form_spec_template=Integer(),
                        level_direction=LevelDirection.UPPER,
                        prefill_fixed_levels=InputHint((0, 0)),
                    ),
                ),
            },
        ),
    )


def podman_containers() -> Dictionary:
    return Dictionary(
        help_text=Help("Thresholds for the podman containers service."),
        elements={
            "total": _simple_levels_element("total"),
            "running": _simple_levels_element("running"),
            "created": _simple_levels_element("created"),
            "paused": _simple_levels_element("paused"),
            "stopped": _simple_levels_element("stopped"),
            "restarting": _simple_levels_element("restarting"),
            "removing": _simple_levels_element("removing"),
            "dead": _simple_levels_element("dead"),
            "exited": _simple_levels_element("exited"),
            "exited_as_non_zero": _simple_levels_element("exited_as_non_zero"),
        },
    )


rule_spec_podman_containers = CheckParameters(
    name="podman_containers",
    title=Title("Podman containers"),
    topic=Topic.APPLICATIONS,
    parameter_form=podman_containers,
    condition=HostCondition(),
)
