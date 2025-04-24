#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, assert_never, Literal

from cmk.plugins.ipmi.lib.ipmi import DiscoveryMode, StateMapping, UserLevels
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    InputHint,
    LevelDirection,
    LevelsType,
    List,
    migrate_to_float_simple_levels,
    ServiceState,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _ignored_dict_elements(when: Literal["discovery", "summary"]) -> Mapping[str, DictElement]:
    match when:
        case "discovery":
            ignored_sensors_help = Help(
                "Names of IPMI sensors that should be ignored during discovery. "
                "The pattern specified here must match exactly the beginning of "
                "the actual sensor name (case sensitive)."
            )
            ignored_sensorsstate_help = Help(
                "IPMI sensors with these states that should be ignored during discovery. "
                "The pattern specified here must match exactly the beginning of the actual "
                "sensor state (case sensitive)."
            )
        case "summary":
            ignored_sensors_help = Help(
                "Names of IPMI sensors that should be ignored when summarizing. "
                "The pattern specified here must match exactly the beginning of "
                "the actual sensor name (case sensitive)."
            )
            ignored_sensorsstate_help = Help(
                "IPMI sensors with these states that should be ignored when summarizing. "
                "The pattern specified here must match exactly the beginning of the actual "
                "sensor state (case sensitive)."
            )
        case _ as unreachable:
            assert_never(unreachable)

    return {
        "ignored_sensors": DictElement(
            required=False,
            parameter_form=List(
                element_template=String(),
                title=Title("Ignore the following IPMI sensors"),
                help_text=ignored_sensors_help,
            ),
        ),
        "ignored_sensorstates": DictElement(
            required=False,
            parameter_form=List(
                element_template=String(),
                title=Title("Ignore the following IPMI sensor states"),
                help_text=ignored_sensorsstate_help,
            ),
        ),
    }


def _migrate_discovery_mode(
    value: object,
) -> DiscoveryMode:
    assert isinstance(value, tuple) and len(value) == 2
    if value[0] == "summarize":
        return "summarize", None
    return "single", value[1]


def _valuespec_inventory_ipmi_rules() -> Dictionary:
    return Dictionary(
        title=Title("IPMI sensor discovery"),
        elements={
            "discovery_mode": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Discovery mode"),
                    migrate=_migrate_discovery_mode,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="summarize",
                            title=Title("Summary of all sensors"),
                            parameter_form=FixedValue(value=None, label=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="single",
                            title=Title("One service per sensor"),
                            parameter_form=Dictionary(
                                elements=_ignored_dict_elements(when="discovery")
                            ),
                        ),
                    ],
                ),
            )
        },
    )


rule_spec_inventory_ipmi_rules = DiscoveryParameters(
    name="inventory_ipmi_rules",
    title=Title("IPMI sensor discovery"),
    topic=Topic.LINUX,
    parameter_form=_valuespec_inventory_ipmi_rules,
)


def _sensor_limits() -> Dictionary:
    return Dictionary(
        elements={
            "sensor_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Sensor name"),
                    help_text=Help(
                        "Enter the name of the sensor. In single mode, this can be read off "
                        "from the service names of the services 'IPMI Sensor ...'."
                    ),
                ),
            ),
            "lower": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    form_spec_template=Float(),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((50.0, 10.0)),
                ),
            ),
            "upper": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    form_spec_template=Float(),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((10.0, 50.0)),
                ),
            ),
        }
    )


def _migrate_sensor_states(value: object) -> list[StateMapping]:
    def _migrate_inner(x: StateMapping | tuple[str, int]) -> StateMapping:
        match x:
            case dict():
                return x
            case tuple():
                assert len(x) == 2
                return {"ipmi_state": x[0], "target_state": x[1]}
            case _:
                raise TypeError(f"Unexpected type {type(x)}")

    assert isinstance(value, list)
    return [_migrate_inner(x) for x in value]


def _migrate_sensor_limits(value: object) -> list[UserLevels]:
    def _migrate_inner(
        x: UserLevels | tuple[str, dict[str, tuple[float, float]]],
    ) -> UserLevels:
        match x:
            case dict():
                return x
            case tuple():
                return UserLevels(
                    sensor_name=x[0],
                    lower=migrate_to_float_simple_levels(x[1].get("lower", None)),
                    upper=migrate_to_float_simple_levels(x[1].get("upper", None)),
                )
            case _:
                raise TypeError(f"Unexpected type {type(x)}")

    assert isinstance(value, list)
    return [_migrate_inner(x) for x in value]


def _parameter_valuespec_ipmi() -> Dictionary:
    elements: dict[str, DictElement[Any]] = {
        "sensor_states": DictElement(
            required=False,
            parameter_form=List(
                element_template=Dictionary(
                    elements={
                        "ipmi_state": DictElement(required=True, parameter_form=String()),
                        "target_state": DictElement(required=True, parameter_form=ServiceState()),
                    },
                ),
                title=Title("Set states of IPMI sensor status texts"),
                help_text=Help(
                    "The pattern specified here must match exactly the beginning of "
                    "the sensor state (case sensitive)."
                ),
                migrate=_migrate_sensor_states,
            ),
        ),
        "numerical_sensor_levels": DictElement(
            required=False,
            parameter_form=List(
                element_template=_sensor_limits(),
                title=Title("Set lower and upper levels for numerical sensors"),
                migrate=_migrate_sensor_limits,
            ),
        ),
    }
    elements.update(_ignored_dict_elements(when="summary"))
    return Dictionary(elements=elements)


rule_spec_ipmi = CheckParameters(
    name="ipmi",
    title=Title("IPMI sensors"),
    topic=Topic.LINUX,
    parameter_form=_parameter_valuespec_ipmi,
    condition=HostAndItemCondition(item_title=Title("The sensor name")),
)
