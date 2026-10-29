#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    Percentage,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _fs_aws_limits(
    resource_title: Title,
    default_limit: int,
    unit: str = "",
    title_default: Title | None = None,
) -> CascadingSingleChoice:
    if title_default is None:
        title_default = Title("Limit from AWS API")
    return CascadingSingleChoice(
        prefill=DefaultValue("set_levels"),
        title=Title("Set limit and levels for %(resource_title)s")
        % {"resource_title": resource_title},
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
        title=Title("AWS v2/DynamoDB limits"),
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


rule_spec_aws_v2_dynamodb_limits = CheckParameters(
    name="aws_v2_dynamodb_limits",
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_aws_dynamodb_limits,
    title=Title("AWS v2/DynamoDB limits"),
    condition=HostAndItemCondition(item_title=Title("Instance name")),
)
