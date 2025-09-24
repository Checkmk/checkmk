#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import TypeVar

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    IECMagnitude,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

Number = TypeVar("Number", int, float)


def _validate_level_factory(
    *validators: Callable[[Number], None],
) -> Callable[[SimpleLevelsConfigModel[Number]], None]:
    def validate(levels: SimpleLevelsConfigModel[Number]) -> None:
        if levels[0] == "no_levels":
            return

        for validator in validators:
            for level in levels[1]:
                validator(level)

    return validate


_validate_positive = _validate_level_factory(NumberInRange(min_value=0))
_validate_percent = _validate_level_factory(NumberInRange(min_value=0, max_value=100))


def _make_condition() -> HostAndItemCondition:
    return HostAndItemCondition(
        item_title=Title("Storage account name"),
    )


def _make_usage_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for the Storage usage"),
        elements={
            "used_capacity_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on used capacity"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.GIBI, IECMagnitude.TEBI]
                    ),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((10 * 1024**3, 100 * 1024**3)),
                ),
            )
        },
    )


def _make_flow_form() -> Dictionary:
    return Dictionary(
        help_text=Help("This ruleset allows you to configure levels for the Storage data flows"),
        elements={
            "transactions_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on transaction count"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((100, 200)),
                ),
            ),
            "ingress_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on ingress data"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.MEBI, IECMagnitude.GIBI]
                    ),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((10 * 1024**2, 100 * 1024**2)),
                ),
            ),
            "egress_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on egress data"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=DataSize(
                        displayed_magnitudes=[IECMagnitude.MEBI, IECMagnitude.GIBI]
                    ),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((10 * 1024**2, 100 * 1024**2)),
                ),
            ),
        },
    )


def _make_performance_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for the Storage latency and availability"
        ),
        elements={
            "server_latency_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on server latency"),
                    help_text=Help(
                        "Average latency used by Azure Storage to process a successful request in milliseconds"
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="ms"),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1_000, 5_000)),
                ),
            ),
            "e2e_latency_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on end-to-end latency"),
                    help_text=Help(
                        "Average end-to-end latency of successful requests made to a storage service in milliseconds"
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="ms"),
                    custom_validate=(_validate_positive,),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((1_000, 5_000)),
                ),
            ),
            "availability_levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels on availability"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(unit_symbol="%"),
                    custom_validate=(_validate_percent,),
                    migrate=migrate_to_float_simple_levels,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue((95.0, 80.0)),
                ),
            ),
        },
    )


rule_spec_azure_storageaccounts_usage = CheckParameters(
    name="azure_storageaccounts_usage",
    title=Title("Azure Storage Usage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_usage_form,
    condition=_make_condition(),
)


rule_spec_azure_storageaccounts_flow = CheckParameters(
    name="azure_storageaccounts_flow",
    title=Title("Azure Storage Data Flow"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_flow_form,
    condition=_make_condition(),
)


rule_spec_azure_storageaccounts_performance = CheckParameters(
    name="azure_storageaccounts_performance",
    title=Title("Azure Storage Performance"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_performance_form,
    condition=_make_condition(),
)
