#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Iterable, Mapping, Sequence

from cmk.gui.form_specs.unstable.validators import HostAddress
from cmk.gui.quick_setup.config_setups.aws.ruleset_helper import formspec_aws_tags
from cmk.plugins.aws.lib import aws_region_to_monitor  # astrein: disable=cmk-module-layer-violation
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)


class _ServiceChoices:
    def __init__(self) -> None:
        self.global_services = [
            MultipleChoiceElement(name="ce", title=Title("Costs and usage (CE)")),
        ]
        self.regional_services = [
            MultipleChoiceElement(name="ec2", title=Title("Elastic Compute Cloud (EC2)")),
            MultipleChoiceElement(name="ebs", title=Title("Elastic Block Storage (EBS)")),
            MultipleChoiceElement(name="s3", title=Title("Simple Storage Service (S3)")),
            MultipleChoiceElement(name="glacier", title=Title("Amazon S3 Glacier (Glacier)")),
            MultipleChoiceElement(name="elb", title=Title("Classic load balancing (ELB)")),
            MultipleChoiceElement(
                name="elbv2", title=Title("Application and network load balancing (ELBv2)")
            ),
            MultipleChoiceElement(name="rds", title=Title("Relational Database Service (RDS)")),
            MultipleChoiceElement(name="cloudwatch_alarms", title=Title("CloudWatch alarms")),
            MultipleChoiceElement(name="dynamodb", title=Title("DynamoDB")),
            MultipleChoiceElement(name="wafv2", title=Title("Web Application Firewall (WAFV2)")),
        ]


service_choices = _ServiceChoices()


# Extended AWS Quick Setup service choices, gated behind the aws_extended license flag
# (CMK-35480). With the flag off (e.g. a Pro-licensed Ultimate site) these are not offered,
# so users cannot select services whose check plugins are unavailable.
_AWS_EXTENDED_GLOBAL_SERVICES = [
    MultipleChoiceElement(name="route53", title=Title("Route53")),
    MultipleChoiceElement(name="cloudfront", title=Title("CloudFront")),
]
_AWS_EXTENDED_REGIONAL_SERVICES = [
    MultipleChoiceElement(name="aws_lambda", title=Title("Lambda")),
    MultipleChoiceElement(name="sns", title=Title("Simple Notification Service (SNS)")),
    MultipleChoiceElement(name="ecs", title=Title("Elastic Container Service (ECS)")),
    MultipleChoiceElement(name="elasticache", title=Title("ElastiCache")),
]


def register_extended_aws_service_choices(choices: _ServiceChoices) -> None:
    """Add the extended AWS service choices to the Quick Setup."""
    choices.global_services.extend(_AWS_EXTENDED_GLOBAL_SERVICES)
    choices.regional_services.extend(_AWS_EXTENDED_REGIONAL_SERVICES)


def _formspec_aws_api_access() -> dict[str, DictElement]:
    return {
        "access": DictElement(
            parameter_form=Dictionary(
                title=Title("Access to AWS API"),
                elements={
                    "global_service_region": DictElement(
                        parameter_form=SingleChoice(
                            title=Title("Use custom region for global AWS services"),
                            elements=[
                                SingleChoiceElement(
                                    title=Title("default (all normal AWS regions)"),
                                    name="default",
                                ),
                                *(
                                    SingleChoiceElement(
                                        title=Title(  # astrein: disable=localization-checker
                                            region
                                        ),
                                        name=region.replace("-", "_"),
                                    )
                                    for region in (
                                        "us-gov-east-1",
                                        "us-gov-west-1",
                                        "cn-north-1",
                                        "cn-northwest-1",
                                    )
                                ),
                            ],
                            prefill=DefaultValue("default"),
                        )
                    ),
                    "role_arn_id": DictElement(
                        parameter_form=Dictionary(
                            title=Title("Use STS AssumeRole to assume a different IAM role"),
                            elements={
                                "role_arn": DictElement(
                                    parameter_form=String(
                                        title=Title("The ARN of the IAM role to assume"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "The Amazon Resource Name (ARN) of the role to assume."
                                        ),
                                    ),
                                    required=True,
                                ),
                                "external_id": DictElement(
                                    parameter_form=String(
                                        title=Title("External ID (optional)"),
                                        field_size=FieldSize.MEDIUM,
                                        help_text=Help(
                                            "A unique identifier that might be required when you assume a role in another "
                                            "account. If the administrator of the account to which the role belongs provided "
                                            "you with an external ID, then provide that value in the External ID parameter. "
                                        ),
                                    ),
                                ),
                            },
                        )
                    ),
                },
            ),
            required=True,
        ),
    }


def _formspec_aws_piggyback_naming_convention() -> dict[str, DictElement]:
    return {
        "piggyback_naming_convention": DictElement(
            parameter_form=SingleChoice(
                title=Title("Piggyback names"),
                elements=[
                    SingleChoiceElement(
                        title=Title("IP - region - instance ID"),
                        name="ip_region_instance",
                    ),
                    SingleChoiceElement(
                        title=Title("Private IP DNS name"), name="private_dns_name"
                    ),
                ],
                help_text=Help(
                    "Each EC2 instance creates a piggyback host.<br><b>Note:</b> "
                    "Not every host name is pingable and changing the piggyback name "
                    "will reset the piggyback host.<br><br><b>IP - Region - Instance "
                    'ID:</b><br>The name consists of "{Private IPv4 '
                    'address}-{Region}-{Instance ID}". This uniquely identifies the '
                    "EC2 instance. It is not possible to ping this host name."
                ),
                prefill=DefaultValue("ip_region_instance"),
            ),
            required=True,
        ),
    }


def _convert_regions(values: object) -> list[str]:
    if not isinstance(values, list):
        raise TypeError(values)
    return [region.replace("-", "_") for region in values]


def quick_setup_stage_1() -> Mapping[str, DictElement]:
    return {
        "access_key_id": DictElement(
            parameter_form=String(
                title=Title("Access key ID"),
                field_size=FieldSize.MEDIUM,
                custom_validate=(
                    validators.LengthInRange(
                        min_value=1,
                        error_msg=Message("Access key ID is required but not specified."),
                    ),
                ),
            ),
            required=True,
        ),
        "secret_access_key": DictElement(
            parameter_form=Password(
                title=Title("Secret access key"),
                custom_validate=(
                    validators.LengthInRange(
                        min_value=1,
                        error_msg=Message("Secret access key is required but not specified."),
                    ),
                ),
            ),
            required=True,
        ),
        **formspec_aws_proxy_details(),
    }


def quick_setup_stage_2(max_regions: int | None = None) -> Mapping[str, DictElement]:
    return {
        "regions_to_monitor": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Regions to monitor"),
                elements=[
                    MultipleChoiceElement(
                        name=name.replace("-", "_"),
                        title=Title(title),  # astrein: disable=localization-checker
                    )
                    for name, title in aws_region_to_monitor()
                ],
                custom_validate=(
                    validators.LengthInRange(
                        min_value=1,
                        max_value=max_regions,
                        error_msg=Message("Please select at least one or more regions to continue.")
                        if max_regions is None
                        else Message(  # astrein: disable=localization-checker
                            f"Please select at least one and at most {max_regions} regions to continue"
                        ),
                    ),
                ),
            ),
            required=True,
        ),
    }


def _get_edition_specific_choices(
    valid_service_choices: Iterable[str],
) -> Callable[[object], Sequence[str]]:
    def inner(value: object) -> Sequence[str]:
        if not isinstance(value, Iterable):
            raise TypeError(value)

        # silently cut off invalid extended-edition choices if aws_extended is off now
        # (e.g. after a license downgrade to Pro).
        return [s for s in value if s in valid_service_choices]

    return inner


def quick_setup_stage_3() -> Mapping[str, DictElement]:
    valid_regional_choices = {c.name for c in service_choices.regional_services}
    valid_global_choices = {c.name for c in service_choices.global_services}
    return {
        "services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Services per region"),
                elements=service_choices.regional_services,
                prefill=DefaultValue(list(valid_regional_choices)),
                # not a real migration: implements edition-specific choice filtering, so a
                # config from a higher edition does not break when those choices are gone.
                migrate=_get_edition_specific_choices(valid_regional_choices),
            ),
            required=True,
        ),
        "global_services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Global services"),
                elements=service_choices.global_services,
                prefill=DefaultValue([]),
                migrate=_get_edition_specific_choices(valid_global_choices),
            ),
            required=True,
        ),
    }


def formspec_aws_proxy_details() -> Mapping[str, DictElement]:
    return {
        "proxy_details": DictElement(
            parameter_form=Dictionary(
                title=Title("Proxy server details"),
                elements={
                    "proxy_host": DictElement(
                        parameter_form=String(
                            title=Title("Proxy host"),
                            custom_validate=[
                                HostAddress(
                                    error_msg=Message("Invalid host name or IP address."),
                                )
                            ],
                        ),
                        required=True,
                    ),
                    "proxy_port": DictElement(
                        parameter_form=Integer(
                            title=Title("Port"),
                            custom_validate=[
                                validators.NumberInRange(
                                    0,
                                    65535,
                                    Message("Port must be between 0 and 65535."),
                                )
                            ],
                        )
                    ),
                    "proxy_user": DictElement(
                        parameter_form=String(title=Title("Username"), field_size=FieldSize.MEDIUM),
                    ),
                    "proxy_password": DictElement(
                        parameter_form=Password(
                            title=Title("Password"),
                        ),
                    ),
                },
            ),
        ),
    }


def formspec_aws_overall_tags() -> Mapping[str, DictElement]:
    return {
        "overall_tags": DictElement(
            parameter_form=formspec_aws_tags(Title("AWS tags")),
            required=True,
        )
    }


def quick_setup_advanced() -> Mapping[str, DictElement]:
    return {
        **_formspec_aws_api_access(),
        **_formspec_aws_piggyback_naming_convention(),
        **formspec_aws_overall_tags(),
    }


def quick_setup_aws_form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Amazon Web Services (AWS)"),
        elements={
            **quick_setup_stage_1(),
            **quick_setup_stage_2(),
            **quick_setup_stage_3(),
            **quick_setup_advanced(),
        },
    )
