#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    ServiceState,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange


def migrate_mapped_states(model: object, state_names: Sequence[str]) -> Mapping[str, object]:
    """Turn the formerly listed (state name, service state) pairs into a mapping

    A state the list left out used to get the service state configured as
    "mapped_states_default" if there was one; it is now set explicitly.
    """
    if not isinstance(model, dict):
        raise TypeError(f"Expected a mapping of parameters, got {model!r}")
    if not isinstance(pairs := model.get("mapped_states"), list):
        return model
    mapped_states = dict(pairs)
    if "mapped_states_default" in model:
        mapped_states = dict.fromkeys(state_names, model["mapped_states_default"]) | mapped_states
    return {**model, "mapped_states": mapped_states}


def _migrate_version(model: object) -> tuple[str, object]:
    match model:
        # The rule used to store ((comparison, version), state) and had no "any" choice.
        case ((str(comparison), str(version)), int(state)):
            return comparison, {"version": version, "state": state}
        case (str(comparison), expectation):
            return comparison, expectation
        case _:
            raise TypeError(f"Expected a version check, got {model!r}")


def _version_expectation() -> Dictionary:
    return Dictionary(
        elements={
            "version": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Version"),
                    custom_validate=(LengthInRange(min_value=1),),
                ),
            ),
            "state": DictElement(
                required=True,
                parameter_form=ServiceState(
                    title=Title("State if the version does not match"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        },
    )


def version_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Check for correct version"),
        help_text=Help(
            "You can make sure that the plug-in is running with a specific or a minimal version."
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="any",
                title=Title("Accept any version"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="at_least",
                title=Title("At least"),
                parameter_form=_version_expectation(),
            ),
            CascadingSingleChoiceElement(
                name="specific",
                title=Title("Specific version"),
                parameter_form=_version_expectation(),
            ),
        ],
        prefill=DefaultValue("at_least"),
        migrate=_migrate_version,
    )
