#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    List,
    MatchingScope,
    migrate_to_float_simple_levels,
    RegularExpression,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_REQUIRED_STATES = {"active": 0, "inactive": 0, "failed": 2}


def _migrate_required_states(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    if not isinstance(states := value.get("states"), dict):
        return value
    return {**value, "states": {**_REQUIRED_STATES, **states}}


def _tolerance_levels(
    title: Title,
    help_text: Help,
    *,
    prefill_levels_type: Literal[LevelsType.NONE, LevelsType.FIXED],
) -> SimpleLevels[float]:
    return SimpleLevels(
        title=title,
        help_text=help_text,
        level_direction=LevelDirection.UPPER,
        form_spec_template=TimeSpan(
            displayed_magnitudes=[
                TimeMagnitude.DAY,
                TimeMagnitude.HOUR,
                TimeMagnitude.MINUTE,
                TimeMagnitude.SECOND,
            ]
        ),
        prefill_levels_type=DefaultValue(prefill_levels_type),
        prefill_fixed_levels=DefaultValue((30.0, 60.0)),
        migrate=migrate_to_float_simple_levels,
    )


def _parameter_form_systemd_units_summary() -> Dictionary:
    return Dictionary(
        elements={
            "disabled_critical": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Treat failed units that are disabled as critical"),
                    help_text=Help(
                        "A failed service that is disabled is also considered for the status of the service. "
                        "Activating this option will cause the service to be CRIT if a failed service is disabled."
                    ),
                    label=Label("Failed units that are disabled will be considered critical"),
                    prefill=DefaultValue(True),
                ),
            ),
            "states": DictElement(
                parameter_form=Dictionary(
                    title=Title("Map systemd states to monitoring states"),
                    elements={
                        "active": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is active"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                            required=True,
                        ),
                        "inactive": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is inactive"),
                                prefill=DefaultValue(ServiceState.OK),
                            ),
                            required=True,
                        ),
                        "failed": DictElement(
                            parameter_form=ServiceState(
                                title=Title("Monitoring state if unit is failed"),
                                prefill=DefaultValue(ServiceState.CRIT),
                            ),
                            required=True,
                        ),
                    },
                ),
            ),
            "states_default": DictElement(
                parameter_form=ServiceState(
                    title=Title("Monitoring state for any other unit state"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "ignored": DictElement(
                parameter_form=List(
                    title=Title("Exclude units matching provided regex patterns"),
                    help_text=Help(
                        "You can optionally define one or multiple regular expressions."
                        " Matching units are excluded."
                        " This allows to ignore services which are known to fail beforehand."
                    ),
                    element_template=RegularExpression(
                        title=Title("Pattern (Regex)"),
                        predefined_help_text=MatchingScope.PREFIX,
                    ),
                    add_element_label=Label("Add pattern"),
                ),
            ),
            "activating_levels": DictElement(
                parameter_form=_tolerance_levels(
                    Title("Tolerance period for 'activating' state"),
                    Help(
                        "Choose time levels for which a unit is allowed to be in an 'activating' state"
                    ),
                    prefill_levels_type=LevelsType.NONE,
                ),
            ),
            "deactivating_levels": DictElement(
                parameter_form=_tolerance_levels(
                    Title("Tolerance period for 'deactivating' state"),
                    Help(
                        "Choose time levels for which a unit is allowed to be in a 'deactivating' state"
                    ),
                    prefill_levels_type=LevelsType.FIXED,
                ),
            ),
            "reloading_levels": DictElement(
                parameter_form=_tolerance_levels(
                    Title("Tolerance period for 'reloading' state"),
                    Help(
                        "Choose time levels for which a unit is allowed to be in a 'reloading' state"
                    ),
                    prefill_levels_type=LevelsType.FIXED,
                ),
            ),
        },
        help_text=Help(
            "This rule set only applies to the summary systemd service and not the individual one."
        ),
        migrate=_migrate_required_states,
    )


rule_spec_systemd_services_summary = CheckParameters(
    name="systemd_services_summary",
    title=Title("Systemd services summary"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_systemd_units_summary,
    condition=HostCondition(),
)

rule_spec_systemd_sockets_summary = CheckParameters(
    name="systemd_sockets_summary",
    title=Title("Systemd sockets summary"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_systemd_units_summary,
    condition=HostCondition(),
)
