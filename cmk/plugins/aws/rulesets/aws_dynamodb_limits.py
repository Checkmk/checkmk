#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.plugins.aws.lib import AWSLimitPercentage, AWSLimits
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    FormSpec,
    Integer,
    Percentage,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _pre_25_to_formspec_migration(
    values: object,
) -> Mapping[str, tuple[Literal["no_levels"], None] | tuple[Literal["set_levels"], AWSLimits]]:
    """
    Migrates the ValueSpecs format of the params to the new FormSpecs format.

    ## ValueSpecs used until Checkmk 2.4
    The old format is a tuple with three values:
    ```
        "number_of_tables": (None | int, None | float, None | float)
        "read_capacity":    (None | int, None | float, None | float)
        "write_capacity":   (None | int, None | float, None | float)
    ```
    ## Resulting in Mapping[str, tuple[Literal["no_levels"], None] | tuple[Literal["set_levels"], AWSLimits]]
    """
    if not isinstance(values, dict):
        raise TypeError("Expected a dictionary for migration of AWS DynamoDB limits")

    possible_settings = {"number_of_tables", "read_capacity", "write_capacity"}
    return {
        setting: _to_formspec_single_migration(values=values, key=setting)
        for setting in possible_settings
        if setting in values
    }


def _to_formspec_single_migration(
    values: Mapping[str, tuple], key: str
) -> tuple[Literal["no_levels"], None] | tuple[Literal["set_levels"], AWSLimits]:
    if all(val is None for val in values[key]) and len(values[key]) == 3:
        return ("no_levels", None)

    if len(values[key]) == 3:
        return (
            "set_levels",
            AWSLimits(
                absolute=(
                    "aws_default_limit" if values[key][0] is None else "aws_limit_value",
                    values[key][0],
                ),
                percentage=AWSLimitPercentage(warn=values[key][1], crit=values[key][2]),
            ),
        )

    if len(values[key]) == 2 and values[key][0] == "set_levels":
        return values[key]

    raise ValueError(
        f"Invalid value for {key}: {values[key]}. Expected a tuple with len of 2 or 3."
    )


def _fs_aws_limits(
    resource_title: Title,
    default_limit: int,
    unit: str = "",
    title_default: Title | None = None,
) -> FormSpec:
    if title_default is None:
        title_default = Title("Limit from AWS API")
    return CascadingSingleChoice(
        prefill=DefaultValue("set_levels"),
        title=Title("Set limit and levels for %s") % resource_title,
        elements=[
            CascadingSingleChoiceElement(
                name="set_levels",
                title=Title("Set levels"),
                parameter_form=Dictionary(
                    title=Title("Set levels"),
                    elements={
                        "absolute": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoice(
                                prefill=DefaultValue("aws_default_limit"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        title=title_default,
                                        name="aws_default_limit",
                                        parameter_form=FixedValue(value=None),
                                    ),
                                    CascadingSingleChoiceElement(
                                        title=resource_title,
                                        name="aws_limit_value",
                                        parameter_form=Integer(
                                            prefill=DefaultValue(default_limit),
                                            unit_symbol=unit,
                                            custom_validate=[validators.NumberInRange(min_value=1)],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        "percentage": DictElement(
                            required=True,
                            parameter_form=Dictionary(
                                title=None,
                                elements={
                                    "warn": DictElement(
                                        parameter_form=Percentage(
                                            title=Title("Warning at"),
                                            prefill=DefaultValue(80.0),
                                        ),
                                        required=True,
                                    ),
                                    "crit": DictElement(
                                        parameter_form=Percentage(
                                            title=Title("Critical at"),
                                            prefill=DefaultValue(90.0),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="no_levels", title=Title("No levels"), parameter_form=FixedValue(value=None)
            ),
        ],
    )


def _formspec_aws_dynamodb_limits() -> Dictionary:
    return Dictionary(
        title=Title("AWS/DynamoDB Limits"),
        migrate=_pre_25_to_formspec_migration,
        elements={
            "number_of_tables": DictElement(
                parameter_form=_fs_aws_limits(
                    resource_title=Title("Number of tables"),
                    default_limit=256,
                    unit="tables",
                    title_default=Title("Default limit set by AWS"),
                ),
            ),
            "read_capacity": DictElement(
                parameter_form=_fs_aws_limits(
                    resource_title=Title("Read capacity"),
                    default_limit=80000,
                    unit="RCU",
                ),
            ),
            "write_capacity": DictElement(
                parameter_form=_fs_aws_limits(
                    resource_title=Title("Write capacity"),
                    default_limit=80000,
                    unit="WCU",
                ),
            ),
        },
    )


rule_spec_aws_dynamodb_limits = CheckParameters(
    name="aws_dynamodb_limits",
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_aws_dynamodb_limits,
    title=Title("AWS/DynamoDB Limits"),
    condition=HostAndItemCondition(item_title=Title("Instance name")),
)
