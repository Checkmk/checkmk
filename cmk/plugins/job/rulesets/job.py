#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.job.lib import ExitCodeState
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    List,
    migrate_to_float_simple_levels,
    ServiceState,
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate_age(value: object) -> SimpleLevelsConfigModel[float]:
    """Turn the levels of pre-2.0 versions into levels that are applied as configured.

    Back then the default was ``(0, 0)``, and the check plug-in skipped levels of zero
    instead of applying them. Rules and autochecks written then still carry that value,
    so it has to keep meaning "no levels".
    """
    if value == (0, 0):
        return "no_levels", None
    return migrate_to_float_simple_levels(value)


def _migrate_exit_code_to_state_map(value: object) -> list[ExitCodeState]:
    def _migrate_entry(entry: ExitCodeState | tuple[int, int]) -> ExitCodeState:
        match entry:
            case dict():
                return entry
            case (int(exit_code), int(state)):
                return ExitCodeState(exit_code=exit_code, state=state)
            case _:
                raise TypeError(f"Unexpected type {type(entry)}")

    assert isinstance(value, list)
    return [_migrate_entry(entry) for entry in value]


def _parameter_form_job() -> Dictionary:
    return Dictionary(
        elements={
            "age": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels(
                    title=Title("Maximum time since last start of job execution"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=_migrate_age,
                ),
            ),
            "exit_code_to_state_map": DictElement(
                parameter_form=List(
                    title=Title("Explicit mapping of job exit codes to states"),
                    help_text=Help(
                        "Here, you can define a mapping between possible exit codes and service "
                        "states. If no mapping is defined, the check becomes CRITICAL when the "
                        "exit code is not 0. If an exit code occurs that is not defined in this "
                        "mapping, the check becomes CRITICAL. If you happen to define the same "
                        "exit code multiple times the last entry will be used."
                    ),
                    element_template=Dictionary(
                        elements={
                            "exit_code": DictElement(
                                required=True,
                                parameter_form=Integer(
                                    title=Title("Exit code"),
                                    prefill=DefaultValue(0),
                                ),
                            ),
                            "state": DictElement(
                                required=True,
                                parameter_form=ServiceState(
                                    title=Title("Resulting state"),
                                    prefill=DefaultValue(ServiceState.OK),
                                ),
                            ),
                        },
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=_migrate_exit_code_to_state_map,
                ),
            ),
        },
        # Superseded by the ruleset "Aggregation options for clustered services".
        ignored_elements=("outcome_on_cluster",),
    )


rule_spec_job = CheckParameters(
    name="job",
    title=Title("mk-job job age"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_job,
    condition=HostAndItemCondition(item_title=Title("Job name")),
)
